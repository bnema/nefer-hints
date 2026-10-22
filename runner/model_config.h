// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include <cmath>
#include <fstream>
#include <iterator>
#include <regex>
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
      if (c != '\\') { out += char(c); continue; }
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
    std::ifstream file(path);
    if (!file) throw std::runtime_error("cannot read model.json: " + path);
    input.assign(std::istreambuf_iterator<char>(file), {});
    if (file.bad()) throw std::runtime_error("cannot read model.json: " + path);
    if (!take('{')) invalid();
    if (!take('}')) {
      do {
        std::string key = string();
        if (!take(':')) invalid();
        space();
        bool is_string = pos < input.size() && input[pos] == '"';
        std::string value;
        if (is_string) value = string();
        else {
          static const std::regex number("-?(0|[1-9][0-9]*)(\\.[0-9]+)?([eE][+-]?[0-9]+)?");
          std::smatch match;
          std::string rest = input.substr(pos);
          if (!std::regex_search(rest, match, number, std::regex_constants::match_continuous)) invalid();
          value = match.str();
          pos += value.size();
        }
        if (key == "name") {
          if (!is_string) invalid();
          name = value;
        } else if (key == "conf" || key == "iou") {
          if (is_string) invalid();
          double n = std::stod(value);
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
