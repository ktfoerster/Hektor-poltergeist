// Deterministic exhaustive counterexample sampler for CEGIS.
// This is deliberately separate from verify.cpp: the unchanged verifier is
// still authoritative, and sat_search.py aborts unless both programs agree on
// the exact obligation and failure counts.
#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <queue>
#include <stdexcept>
#include <utility>
#include <vector>
using namespace std;

int policy[7][128][8][2];

static uint64_t splitmix64(uint64_t x) {
  x += 0x9e3779b97f4a7c15ULL;
  x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
  x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
  return x ^ (x >> 31);
}

int main(int argc, char **argv) {
  try {
    if (argc != 2) throw runtime_error("policy path required");
    ifstream f(argv[1]);
    int n, t;
    if (!(f >> n >> t) || n < 2 || n > 7 || t < 0 || t >= n)
      throw runtime_error("header");
    vector<pair<int, int>> edges;
    int host[7] = {};
    for (int u = 0; u < n; ++u) for (int v = u + 1; v < n; ++v)
      if (n != 7 || !((u == 3 && v == 4) || (u == 5 && v == 6))) {
        edges.push_back({u, v}); host[u] |= 1 << v; host[v] |= 1 << u;
      }
    for (auto &a : policy) for (auto &b : a) for (auto &c : b)
      for (int &d : c) d = -1;
    int u, L, p, b, x;
    while (f >> u) {
      if (!(f >> L >> p >> b >> x)) throw runtime_error("truncated row");
      if (u < 0 || u >= n || u == t || L <= 0 || L >= 1 << n ||
          (L & ~host[u]) || p < -1 || p >= n || b < 0 || b > 1 ||
          (p == -1 && b != 0) || (p >= 0 && !(L >> p & 1)) ||
          x < 0 || x >= 2 * n || !(L >> (x / 2) & 1))
        throw runtime_error("illegal row");
      int &slot = policy[u][L][p + 1][b];
      if (slot != -1) throw runtime_error("duplicate");
      slot = x;
    }
    if (!f.eof()) throw runtime_error("malformed input");
    for (u = 0; u < n; ++u) if (u != t)
      for (L = 1; L < 1 << n; ++L) if (!(L & ~host[u])) {
        if (policy[u][L][0][0] < 0) throw runtime_error("missing injection");
        for (p = 0; p < n; ++p) if (L >> p & 1) for (b = 0; b < 2; ++b)
          if (policy[u][L][p + 1][b] < 0) throw runtime_error("missing transit");
      }

    // Keep the 16 failing masks with the lowest deterministic hash. This
    // avoids the old bias toward the first numerically enumerated residuals
    // without changing the number of residuals learned per candidate.
    using RankedMask = pair<uint64_t, int>;
    priority_queue<RankedMask> sample;
    long long obligations = 0, failures = 0;
    for (int mask = 0; mask < (1 << edges.size()); ++mask) {
      int adj[7] = {};
      for (int i = 0; i < (int)edges.size(); ++i) if (mask >> i & 1) {
        auto [a, c] = edges[i]; adj[a] |= 1 << c; adj[c] |= 1 << a;
      }
      int connected = 1 << t;
      bool change = true;
      while (change) {
        int before = connected;
        for (int a = 0; a < n; ++a) if (connected >> a & 1)
          connected |= adj[a];
        change = before != connected;
      }
      bool failed_mask = false;
      for (int s = 0; s < n; ++s) if (s != t && (connected >> s & 1)) {
        ++obligations;
        bool seen[7][7][2] = {};
        int a = s, prev = -1, bit = 0;
        bool ok = true;
        while (a != t) {
          if (prev >= 0) {
            if (seen[a][prev][bit]) { ok = false; break; }
            seen[a][prev][bit] = true;
          }
          int next = policy[a][adj[a]][prev + 1][bit];
          prev = a; a = next / 2; bit = next % 2;
        }
        if (!ok) { ++failures; failed_mask = true; }
      }
      if (failed_mask) {
        RankedMask item = {splitmix64((uint64_t)mask ^ 0x4b3131313232ULL), mask};
        if (sample.size() < 16) sample.push(item);
        else if (item < sample.top()) { sample.pop(); sample.push(item); }
      }
    }
    vector<int> bad;
    while (!sample.empty()) { bad.push_back(sample.top().second); sample.pop(); }
    sort(bad.begin(), bad.end());
    cout << "{\"masks\":" << (1 << edges.size())
         << ",\"obligations\":" << obligations
         << ",\"failures\":" << failures
         << ",\"selector\":\"splitmix64-lowest-16\",\"counterexamples\":[";
    for (size_t i = 0; i < bad.size(); ++i) {
      if (i) cout << ',';
      cout << bad[i];
    }
    cout << "]}\n";
  } catch (exception &e) {
    cerr << e.what() << '\n';
    return 2;
  }
}
