// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include <array>
#include <cmath>
#include <fstream>
#include <set>
#include <stdexcept>
#include <string>

// Deliberately accepts only a flat JSON object of strings and numbers.
class ModelConfig {
  std::string input;
  size_t pos = 0;
  [[noreturn]] void invalid() const {
    throw std::runtime_error("invalid model.json");
  }
  void space() {
    while (pos < input.size() && (input[pos] == ' ' || input[pos] == '\t' ||
           input[pos] == '\r' || input[pos] == '\n')) ++pos;
  }
  bool take(char c) {
    space();
    if (pos < input.size() && input[pos] == c) { ++pos; return true; }
    return false;
  }
  unsigned hex() {
    unsigned n = 0;
    for (int i = 0; i < 4; ++i) {
      if (pos == input.size()) invalid();
      char c = input[pos++];
      n <<= 4;
      if (c >= '0' && c <= '9') n += c - '0';
      else if (c >= 'a' && c <= 'f') n += c - 'a' + 10;
      else if (c >= 'A' && c <= 'F') n += c - 'A' + 10;
      else invalid();
    }
    return n;
  }
  std::string string() {
    if (!take('"')) invalid();
    std::string out;
    while (pos < input.size()) {
      unsigned char c = input[pos++];
      if (c == '"') return out;
      if (c < 32) invalid();
      if (c != '\\') {
        out += char(c);
        if (c < 0x80) continue;
        unsigned u, minimum;
        int remaining;
        if (c >= 0xc2 && c <= 0xdf) { u = c & 0x1f; minimum = 0x80; remaining = 1; }
        else if (c >= 0xe0 && c <= 0xef) { u = c & 0x0f; minimum = 0x800; remaining = 2; }
        else if (c >= 0xf0 && c <= 0xf4) { u = c & 0x07; minimum = 0x10000; remaining = 3; }
        else invalid();
        for (int i = 0; i < remaining; ++i) {
          if (pos == input.size()) invalid();
          unsigned char next = input[pos++];
          if ((next & 0xc0) != 0x80) invalid();
          u = (u << 6) | (next & 0x3f);
          out += char(next);
        }
        if (u < minimum || u > 0x10ffff || (u >= 0xd800 && u <= 0xdfff)) invalid();
        continue;
      }
      if (pos == input.size()) invalid();
      c = input[pos++];
      switch (c) {
      case '"': case '\\': case '/': out += char(c); break;
      case 'b': out += '\b'; break;
      case 'f': out += '\f'; break;
      case 'n': out += '\n'; break;
      case 'r': out += '\r'; break;
      case 't': out += '\t'; break;
      case 'u': {
        unsigned u = hex();
        if (u >= 0xd800 && u <= 0xdbff) {
          if (pos + 2 > input.size() || input.substr(pos, 2) != "\\u") invalid();
          pos += 2;
          unsigned lo = hex();
          if (lo < 0xdc00 || lo > 0xdfff) invalid();
          u = 0x10000 + ((u - 0xd800) << 10) + lo - 0xdc00;
        } else if (u >= 0xdc00 && u <= 0xdfff) invalid();
        if (u <= 0x7f) out += char(u);
        else {
          if (u > 0xffff) out += char(0xf0 | (u >> 18));
          if (u > 0x7ff) out += char((u > 0xffff ? 0x80 : 0xe0) | ((u >> 12) & 0x3f));
          out += char((u > 0x7ff ? 0x80 : 0xc0) | ((u >> 6) & 0x3f));
          out += char(0x80 | (u & 0x3f));
        }
        break;
      }
      default: invalid();
      }
    }
    invalid();
  }
public:
  void load(const std::string &path, float &conf, float &iou, std::string &name) {
    std::ifstream file(path, std::ios::binary);
    if (!file) throw std::runtime_error("cannot read model.json: " + path);
    constexpr size_t limit = 64 * 1024;
    std::array<char, limit + 1> buffer;
    file.read(buffer.data(), buffer.size());
    if (file.bad()) throw std::runtime_error("cannot read model.json: " + path);
    if (file.gcount() > static_cast<std::streamsize>(limit)) invalid();
    input.assign(buffer.data(), static_cast<size_t>(file.gcount()));
    pos = 0;
    std::set<std::string> keys;
    if (!take('{')) invalid();
    if (!take('}')) {
      do {
        std::string key = string();
        if (!keys.insert(key).second) invalid();
        if (!take(':')) invalid();
        space();
        bool is_string = pos < input.size() && input[pos] == '"';
        std::string value;
        if (is_string) value = string();
        else {
          size_t start = pos;
          auto digit = [&] { return pos < input.size() && input[pos] >= '0' && input[pos] <= '9'; };
          auto digits = [&] {
            if (!digit()) invalid();
            do { ++pos; } while (digit());
          };
          if (pos < input.size() && input[pos] == '-') ++pos;
          if (pos < input.size() && input[pos] == '0') ++pos;
          else digits();
          if (pos < input.size() && input[pos] == '.') { ++pos; digits(); }
          if (pos < input.size() && (input[pos] == 'e' || input[pos] == 'E')) {
            ++pos;
            if (pos < input.size() && (input[pos] == '+' || input[pos] == '-')) ++pos;
            digits();
          }
          value = input.substr(start, pos - start);
        }
        if (key == "name") {
          if (!is_string) invalid();
          name = value;
        } else if (key == "conf" || key == "iou") {
          if (is_string) invalid();
          double n;
          try { n = std::stod(value); }
          catch (const std::exception &) { invalid(); }
          if (!std::isfinite(n) || n > 1 || (key == "conf" ? n <= 0 : n < 0)) invalid();
          float f = float(n);
          if (key == "conf") { if (f <= 0) invalid(); conf = f; }
          else iou = f;
        }
      } while (take(','));
      if (!take('}')) invalid();
    }
    space();
    if (pos != input.size()) invalid();
  }
};
