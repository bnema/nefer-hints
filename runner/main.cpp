// SPDX-License-Identifier: AGPL-3.0-only
#include "model_config.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <gpu.h>
#include <iostream>
#include <limits>
#include <net.h>
#include <stdexcept>
#include <string>
#include <vector>
using Clock = std::chrono::steady_clock;
static void readbytes(void *p, size_t n) {
  if (fread(p, 1, n, stdin) != n)
    throw std::runtime_error("truncated frame");
}
static uint32_t u32() {
  unsigned char b[4];
  readbytes(b, 4);
  return uint32_t(b[0]) | uint32_t(b[1]) << 8 | uint32_t(b[2]) << 16 |
         uint32_t(b[3]) << 24;
}
static void put32(uint32_t n) {
  unsigned char b[4];
  for (int i = 0; i < 4; i++)
    b[i] = n >> (8 * i);
  if (fwrite(b, 1, 4, stdout) != 4)
    throw std::runtime_error("stdout closed");
}
static void put64(uint64_t n) {
  put32(n);
  put32(n >> 32);
}
static float f32() {
  uint32_t n = u32();
  float f;
  memcpy(&f, &n, 4);
  return f;
}
static void putfloat(float f) {
  uint32_t n;
  memcpy(&n, &f, 4);
  put32(n);
}
static void text(const std::string &s) {
  put32(s.size());
  fwrite(s.data(), 1, s.size(), stdout);
}
static void flush() {
  if (fflush(stdout))
    throw std::runtime_error("stdout closed");
}
static void response(uint64_t seq, uint32_t status) {
  fwrite("NHRS", 1, 4, stdout);
  put32(1);
  put64(seq);
  put32(status);
}
static void error(uint64_t seq, uint32_t status, const std::string &s) {
  response(seq, status);
  text(s);
  flush();
}
struct Rect {
  int64_t x, y, w, h;
};
struct Box {
  float x1, y1, x2, y2, score;
  uint32_t region;
};
static float iou(const Box &a, const Box &b) {
  float inter = std::max(0.f, std::min(a.x2, b.x2) - std::max(a.x1, b.x1)) *
                std::max(0.f, std::min(a.y2, b.y2) - std::max(a.y1, b.y1));
  return inter / ((a.x2 - a.x1) * (a.y2 - a.y1) +
                  (b.x2 - b.x1) * (b.y2 - b.y1) - inter + 1e-9f);
}
struct Detector {
  ncnn::Net net, rectnet;
  int size = 1280, maxdet = 1000;
  float conf = .05f, threshold = .7f;
  bool fp32 = false;
  std::vector<Box> detect(const std::vector<unsigned char> &pixels,
                          uint32_t stride, Rect r, uint32_t region,
                          float confidence, float &ms, bool allow_rect = true) {
    double scale = std::min(double(size) / r.w, double(size) / r.h);
    int nw = std::nearbyint(r.w * scale), nh = std::nearbyint(r.h * scale);
    bool rectangular = allow_rect && r.w * 9 == r.h * 16;
    int dw = rectangular ? (size - nw) % 32 : size - nw,
        dh = rectangular ? (size - nh) % 32 : size - nh;
    int left = std::round(dw / 2. - .1), top = std::round(dh / 2. - .1);
    // ncnn's bilinear resize operates directly on the strided BGRA crop.
    auto resized = ncnn::Mat::from_pixels_resize(
        pixels.data() + r.y * stride + r.x * 4, ncnn::Mat::PIXEL_BGRA2RGB,
        int(r.w), int(r.h), int(stride), nw, nh);
    ncnn::Mat input;
    ncnn::copy_make_border(resized, input, top, dh - top, left, dw - left,
                           ncnn::BORDER_CONSTANT, 114.f);
    const float norm[3] = {1 / 255.f, 1 / 255.f, 1 / 255.f};
    input.substract_mean_normalize(nullptr, norm);
    auto start = Clock::now();
    auto ex = (rectangular ? rectnet : net).create_extractor();
    ncnn::Mat out;
    if (ex.input("in0", input) || ex.extract("out0", out))
      throw std::runtime_error("ncnn inference failed");
    ms +=
        std::chrono::duration<float, std::milli>(Clock::now() - start).count();
    if (out.dims != 2 || out.h != 5)
      throw std::runtime_error("expected YOLO output [5,N]");
    std::vector<Box> candidates;
    for (int j = 0; j < out.w; j++) {
      float score = out.row(4)[j];
      if (!std::isfinite(score) || score <= confidence)
        continue;
      float x = out.row(0)[j], y = out.row(1)[j], w = out.row(2)[j],
            h = out.row(3)[j];
      if (!std::isfinite(x + y + w + h) || w < 0 || h < 0)
        continue;
      candidates.push_back(
          {x - w / 2, y - h / 2, x + w / 2, y + h / 2, score, region});
    }
    std::stable_sort(
        candidates.begin(), candidates.end(),
        [](const Box &a, const Box &b) { return a.score > b.score; });
    if (candidates.size() > 30000)
      candidates.resize(30000);
    std::vector<Box> keep;
    for (auto b : candidates) {
      bool suppressed = false;
      for (const auto &k : keep)
        if (iou(b, k) > threshold) {
          suppressed = true;
          break;
        }
      if (!suppressed)
        keep.push_back(b);
      if (int(keep.size()) == maxdet)
        break;
    }
    for (auto &b : keep) {
      b.x1 = r.x + std::clamp(float((b.x1 - left) / scale), 0.f, float(r.w));
      b.x2 = r.x + std::clamp(float((b.x2 - left) / scale), 0.f, float(r.w));
      b.y1 = r.y + std::clamp(float((b.y1 - top) / scale), 0.f, float(r.h));
      b.y2 = r.y + std::clamp(float((b.y2 - top) / scale), 0.f, float(r.h));
    }
    return keep;
  }
};
int main(int argc, char **argv) {
  signal(SIGPIPE, SIG_IGN);
  Detector d;
  std::string model, gpu = "auto", device = "CPU";
  bool hello = false, conf_set = false, iou_set = false;
  std::string model_name;
  try {
    for (int i = 1; i < argc; i++) {
      std::string a = argv[i];
      if (a == "--fp32") {
        d.fp32 = true;
        continue;
      }
      if (i + 1 == argc)
        throw std::runtime_error("missing option value");
      std::string v = argv[++i];
      if (a == "--model")
        model = v;
      else if (a == "--imgsz")
        d.size = std::stoi(v);
      else if (a == "--conf") {
        d.conf = std::stof(v);
        conf_set = true;
      } else if (a == "--iou") {
        d.threshold = std::stof(v);
        iou_set = true;
      }
      else if (a == "--max-det")
        d.maxdet = std::stoi(v);
      else if (a == "--gpu")
        gpu = v;
      else
        throw std::runtime_error("unknown option: " + a);
    }
    if (model.empty()) throw std::runtime_error("missing --model");
    std::filesystem::path metadata;
    if (std::filesystem::is_directory(model)) {
      metadata = std::filesystem::path(model) / "model.json";
      model += "/icon_detect-" + std::to_string(d.size);
    } else {
      if (model.size() > 11 && model.substr(model.size() - 11) == ".ncnn.param")
        model.resize(model.size() - 11);
      metadata = model + ".json";
      if (!std::filesystem::exists(metadata))
        metadata = std::filesystem::path(model).parent_path() / "model.json";
    }
    if (std::filesystem::exists(metadata)) {
      float conf = d.conf, threshold = d.threshold;
      ModelConfig().load(metadata.string(), conf, threshold, model_name);
      if (!conf_set) d.conf = conf;
      if (!iou_set) d.threshold = threshold;
    }
    if (model.empty() || d.size < 32 || d.size > 4096 || d.size % 32 ||
        d.maxdet < 1 || d.maxdet > 10000 || !std::isfinite(d.conf) ||
        d.conf <= 0 || d.conf > 1 || !std::isfinite(d.threshold) ||
        d.threshold < 0 || d.threshold > 1)
      throw std::runtime_error("invalid options");
    ncnn::create_gpu_instance();
    int index = -1;
    if (gpu == "auto") {
      if (ncnn::get_gpu_count() > 0)
        index = 0;
    } else if (gpu != "cpu") {
      size_t used;
      index = std::stoi(gpu, &used);
      if (used != gpu.size() || index < 0 || index >= ncnn::get_gpu_count())
        throw std::runtime_error("invalid GPU index");
    }
    d.net.opt.num_threads = 8;
    if (index >= 0) {
      d.net.opt.use_vulkan_compute = true;
      d.net.set_vulkan_device(index);
      device = ncnn::get_gpu_info(index).device_name();
    }
    if (d.fp32)
      d.net.opt.use_fp16_packed = d.net.opt.use_fp16_storage =
          d.net.opt.use_fp16_arithmetic = false;
    d.rectnet.opt = d.net.opt;
    if (index >= 0)
      d.rectnet.set_vulkan_device(index);
    if (d.net.load_param((model + ".ncnn.param").c_str()) ||
        d.net.load_model((model + ".ncnn.bin").c_str()) ||
        d.rectnet.load_param((model + "-rect.ncnn.param").c_str()) ||
        d.rectnet.load_model((model + "-rect.ncnn.bin").c_str()))
      throw std::runtime_error("cannot load square/rect model");
    std::vector<unsigned char> warm(32 * 32 * 4, 114);
    float ms = 0;
    d.detect(warm, 128, {0, 0, 32, 32}, 0, d.conf, ms);
    std::vector<unsigned char> wide(16 * 9 * 4, 114);
    d.detect(wide, 64, {0, 0, 16, 9}, 0, d.conf, ms);
    std::cerr << "device: " << device << "; fp32=" << d.fp32
              << "; conf=" << d.conf << "; iou=" << d.threshold;
    if (!model_name.empty()) std::cerr << "; model=" << model_name;
    std::cerr << "\n";
    fwrite("NHNT", 1, 4, stdout);
    put32(1);
    put32(0);
    text(device);
    put32(d.size);
    flush();
    hello = true;
    while (true) {
      bool known = false;
      uint64_t seq = 0;
      try {
        char magic[4];
        size_t got = fread(magic, 1, 4, stdin);
        if (got == 0 && feof(stdin))
          return 0;
        if (got != 4)
          throw std::runtime_error("truncated magic");
        if (memcmp(magic, "NHRQ", 4))
          throw std::runtime_error("bad magic");
        uint32_t version = u32();
        seq = u32();
        seq |= uint64_t(u32()) << 32;
        known = true;
        if (version != 1)
          throw std::runtime_error("bad version");
        uint32_t w = u32(), h = u32(), stride = u32(), format = u32(),
                 nr = u32();
        // Also bound byte length: a tiny width with an enormous stride is
        // unsafe.
        uint64_t bytes = uint64_t(stride) * h;
        if (uint64_t(w) * h > (1ull << 28) ||
            uint64_t(stride) < uint64_t(w) * 4 || bytes > (1ull << 30))
          throw std::runtime_error("unsafe dimensions/stride");
        if (nr > 65536)
          throw std::runtime_error("unsafe region count");
        std::string invalid;
        if (!w || !h || format != 1 || nr > 64)
          invalid = "invalid dimensions, format or region count";
        std::vector<Rect> regions;
        for (uint32_t i = 0; i < nr; i++) {
          int64_t x = int32_t(u32()), y = int32_t(u32());
          uint32_t rw = u32(), rh = u32();
          int64_t x2 = std::clamp(x + rw, int64_t(0), int64_t(w)),
                  y2 = std::clamp(y + rh, int64_t(0), int64_t(h));
          x = std::clamp(x, int64_t(0), int64_t(w));
          y = std::clamp(y, int64_t(0), int64_t(h));
          if (x2 <= x || y2 <= y)
            invalid = "empty clipped region";
          if (nr <= 64)
            regions.push_back({x, y, x2 - x, y2 - y});
        }
        float confidence = f32();
        if (!std::isfinite(confidence) || confidence > 1)
          invalid = "invalid confidence";
        if (confidence <= 0)
          confidence = d.conf;
        std::vector<unsigned char> pixels;
        if (invalid.empty()) {
          pixels.resize(bytes);
          readbytes(pixels.data(), bytes);
        } else {
          unsigned char discard[8192];
          for (uint64_t n = bytes; n;) {
            size_t chunk = std::min<uint64_t>(n, sizeof discard);
            readbytes(discard, chunk);
            n -= chunk;
          }
        }
        if (!invalid.empty()) {
          error(seq, 1, invalid);
          continue;
        }
        if (nr == 0)
          regions.push_back({0, 0, w, h});
        try {
          std::vector<Box> boxes;
          float elapsed = 0;
          for (size_t i = 0; i < regions.size(); i++) {
            auto b = d.detect(pixels, stride, regions[i], i, confidence,
                              elapsed, nr == 0);
            boxes.insert(boxes.end(), b.begin(), b.end());
          }
          response(seq, 0);
          putfloat(elapsed);
          put32(boxes.size());
          for (auto b : boxes) {
            putfloat(b.x1);
            putfloat(b.y1);
            putfloat(b.x2);
            putfloat(b.y2);
            putfloat(b.score);
            put32(b.region);
          }
          flush();
        } catch (const std::exception &e) {
          error(seq, 2, e.what());
        }
      } catch (const std::exception &e) {
        std::cerr << e.what() << "\n";
        if (known)
          error(seq, 1, e.what());
        return 2;
      }
    }
  } catch (const std::exception &e) {
    std::cerr << e.what() << "\n";
    if (!hello) {
      fwrite("NHNT", 1, 4, stdout);
      put32(1);
      put32(1);
      text(e.what());
      flush();
    }
    return 1;
  }
}
