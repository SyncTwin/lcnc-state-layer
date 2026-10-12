// SPDX-License-Identifier: GPL-2.0-or-later
// Encoding benchmark on recorded EMC_STAT updates (C++ side).
//
// usage: bench CORPUS.jsonl REPEATS OUT.csv TRACE_LABEL PERIOD_S
//
// CORPUS: one linuxcnc.stat dict per line (bench/prepare.py from a trace).
// Every variant processes the same ticks in order.  Encode = native struct ->
// bytes, decode = bytes -> native struct (full updates) or -> client DOM
// (merge patch), so all variants start and end at the same place.  Per
// message the median over REPEATS passes is taken; the CSV gets median and
// p95 over messages.  One untimed warm-up pass precedes; its first message is
// reported as the cold cost.  Clock: std::chrono::steady_clock.
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <functional>
#include <iostream>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>
#include <flatbuffers/flatbuffers.h>
#include "emc_native.hh"

using json = nlohmann::json;
using clk = std::chrono::steady_clock;

static double us(clk::duration d) { return std::chrono::duration<double, std::micro>(d).count(); }

static double pct(std::vector<double> v, double p) {
    if (v.empty()) return 0;
    std::sort(v.begin(), v.end());
    size_t i = (size_t)(p * (v.size() - 1) + 0.5);
    return v[std::min(i, v.size() - 1)];
}
static double mean(const std::vector<double>& v) {
    double s = 0;
    for (double x : v) s += x;
    return v.empty() ? 0 : s / v.size();
}

// RFC 7396 merge patch from a to b (objects); nlohmann has merge_patch()
// (apply) but no generator.
static json create_merge_patch(const json& a, const json& b) {
    json p = json::object();
    for (auto it = a.begin(); it != a.end(); ++it)
        if (!b.contains(it.key())) p[it.key()] = nullptr;
    for (auto it = b.begin(); it != b.end(); ++it) {
        auto ai = a.find(it.key());
        if (ai == a.end()) {
            p[it.key()] = *it;
        } else if (!(*ai == *it) || ai->type() != it->type()) {
            if (ai->is_object() && it->is_object()) {
                json sub = create_merge_patch(*ai, *it);
                if (!sub.empty()) p[it.key()] = std::move(sub);
            } else {
                p[it.key()] = *it;
            }
        }
    }
    return p;
}

// "arrays as objects keyed by index" data model (Machinetalk-style index
// deltas expressed in RFC 7396): only arrays of objects, or all arrays.
static json objidx(const json& j, bool all_arrays) {
    if (j.is_object()) {
        json o = json::object();
        for (auto it = j.begin(); it != j.end(); ++it) o[it.key()] = objidx(*it, all_arrays);
        return o;
    }
    if (j.is_array() && (all_arrays || (!j.empty() && j[0].is_object()))) {
        json o = json::object();
        for (size_t i = 0; i < j.size(); i++) o[std::to_string(i)] = objidx(j[i], all_arrays);
        return o;
    }
    return j;
}

struct Row {
    std::string lib, variant, note;
    size_t ticks = 0, msgs = 0;
    std::vector<double> bytes, enc, dec, diff, apply;
    double cold_enc = 0, cold_dec = 0;
};

static std::vector<native::EmcStat> S;
static std::vector<json> D;
static int R = 20;

// run f(i, timed) for every tick, R timed passes + 1 warm-up; f fills per
// message times into the vectors passed, returns false if no message
template <class F>
static void passes(Row& r, F f) {
    size_t n = S.size();
    std::vector<std::vector<double>> enc(n), dec(n), dif(n), app(n);
    std::vector<double> bytes(n, -1);
    for (int pass = 0; pass <= R; pass++) {
        for (size_t i = 0; i < n; i++) {
            double e = 0, d = 0, df = 0, ap = 0;
            long b = f(i, e, d, df, ap);
            if (pass == 0) {
                if (i == 0 || (r.cold_enc == 0 && b >= 0)) { r.cold_enc = e; r.cold_dec = d; }
                continue;
            }
            if (b < 0) continue;  // no message for this tick
            bytes[i] = b;
            enc[i].push_back(e); dec[i].push_back(d); dif[i].push_back(df); app[i].push_back(ap);
        }
    }
    r.ticks = n;
    for (size_t i = 0; i < n; i++) {
        if (bytes[i] < 0) continue;
        r.msgs++;
        r.bytes.push_back(bytes[i]);
        r.enc.push_back(pct(enc[i], 0.5));
        r.dec.push_back(pct(dec[i], 0.5));
        r.diff.push_back(pct(dif[i], 0.5));
        r.apply.push_back(pct(app[i], 0.5));
    }
}

using Ser = std::function<std::vector<uint8_t>(const json&)>;
using Des = std::function<json(const std::vector<uint8_t>&)>;

static std::vector<uint8_t> as_bytes(const std::string& s) { return {s.begin(), s.end()}; }

static Row full_dom(const std::string& lib, const std::string& variant, Ser ser, Des des) {
    Row r{lib, variant};
    native::EmcStat out;
    passes(r, [&](size_t i, double& e, double& d, double&, double&) -> long {
        auto t0 = clk::now();
        json j = S[i];
        auto buf = ser(j);
        auto t1 = clk::now();
        json k = des(buf);
        k.get_to(out);
        auto t2 = clk::now();
        e = us(t1 - t0); d = us(t2 - t1);
        return (long)buf.size();
    });
    if (!(out == S.back())) r.note = "ROUNDTRIP MISMATCH";
    return r;
}

static Row patch_dom(const std::string& lib, const std::string& variant, Ser ser, Des des,
                     int model /*0 plain, 1 objidx structs, 2 objidx all*/) {
    Row r{lib, variant};
    auto view = [&](const native::EmcStat& s) {
        json j = s;
        return model ? objidx(j, model == 2) : j;
    };
    json server_prev, client;
    passes(r, [&](size_t i, double& e, double& d, double& df, double& ap) -> long {
        if (i == 0) { server_prev = view(S[0]); client = server_prev; return -1; }
        auto t0 = clk::now();
        json cur = view(S[i]);
        auto t1 = clk::now();
        json p = create_merge_patch(server_prev, cur);
        auto t2 = clk::now();
        server_prev = std::move(cur);
        if (p.empty()) { e = us(t2 - t0); df = us(t2 - t1); return -1; }
        auto buf = ser(p);
        auto t3 = clk::now();
        json q = des(buf);
        auto t4 = clk::now();
        client.merge_patch(q);
        auto t5 = clk::now();
        e = us(t3 - t0); df = us(t2 - t1); d = us(t5 - t3); ap = us(t5 - t4);
        return (long)buf.size();
    });
    if (!(client == view(S.back()))) r.note = "ROUNDTRIP MISMATCH";
    return r;
}

static Row fb_full() {
    Row r{"flatbuffers", "fb_full"};
    flatbuffers::FlatBufferBuilder b(16384);
    native::EmcStat out;
    passes(r, [&](size_t i, double& e, double& d, double&, double&) -> long {
        auto t0 = clk::now();
        b.Clear();
        native::pack_full(b, S[i]);
        auto t1 = clk::now();
        flatbuffers::Verifier v(b.GetBufferPointer(), b.GetSize());
        if (!v.VerifyBuffer<EMC::EmcStat>(nullptr)) throw std::runtime_error("verify");
        native::unpack_full(flatbuffers::GetRoot<EMC::EmcStat>(b.GetBufferPointer()), out);
        auto t2 = clk::now();
        e = us(t1 - t0); d = us(t2 - t1);
        return (long)b.GetSize();
    });
    if (!(out == S.back())) r.note = "ROUNDTRIP MISMATCH";
    return r;
}

// zero-copy read of a DRO-sized subset after verification
static Row fb_read5() {
    Row r{"flatbuffers", "fb_full_read5"};
    r.note = "decode = verify + read task_state, interp_state, motion_line, current_vel, position";
    flatbuffers::FlatBufferBuilder b(16384);
    volatile double sink = 0;
    passes(r, [&](size_t i, double& e, double& d, double&, double&) -> long {
        auto t0 = clk::now();
        b.Clear();
        native::pack_full(b, S[i]);
        auto t1 = clk::now();
        flatbuffers::Verifier v(b.GetBufferPointer(), b.GetSize());
        if (!v.VerifyBuffer<EMC::EmcStat>(nullptr)) throw std::runtime_error("verify");
        auto t = flatbuffers::GetRoot<EMC::EmcStat>(b.GetBufferPointer());
        sink = sink + t->task_state() + t->interp_state() + t->motion_line() + t->current_vel() +
               t->position()->x() + t->position()->y() + t->position()->z();
        auto t2 = clk::now();
        e = us(t1 - t0); d = us(t2 - t1);
        return (long)b.GetSize();
    });
    return r;
}

static Row json_read5() {
    Row r{"nlohmann", "json_full_read5"};
    r.note = "decode = parse to DOM + read the same 5 fields";
    volatile double sink = 0;
    passes(r, [&](size_t i, double& e, double& d, double&, double&) -> long {
        auto t0 = clk::now();
        json j = S[i];
        std::string s = j.dump();
        auto t1 = clk::now();
        json k = json::parse(s);
        sink = sink + k["task_state"].get<int>() + k["interp_state"].get<int>() +
               k["motion_line"].get<int>() + k["current_vel"].get<double>() +
               k["position"][0].get<double>() + k["position"][1].get<double>() +
               k["position"][2].get<double>();
        auto t2 = clk::now();
        e = us(t1 - t0); d = us(t2 - t1);
        return (long)s.size();
    });
    return r;
}

static Row fb_delta() {
    Row r{"flatbuffers", "fb_delta"};
    r.note = "EmcStatDelta: changed fields only (optional scalars), arrays whole";
    flatbuffers::FlatBufferBuilder b(16384);
    native::EmcStat client;
    passes(r, [&](size_t i, double& e, double& d, double& df, double&) -> long {
        if (i == 0) { client = S[0]; return -1; }
        auto t0 = clk::now();
        b.Clear();
        bool any = native::pack_delta(b, S[i - 1], S[i]);
        auto t1 = clk::now();
        e = us(t1 - t0); df = e;
        if (!any) return -1;
        flatbuffers::Verifier v(b.GetBufferPointer(), b.GetSize());
        if (!v.VerifyBuffer<EMC::EmcStatDelta>(nullptr)) throw std::runtime_error("verify");
        native::apply_delta(flatbuffers::GetRoot<EMC::EmcStatDelta>(b.GetBufferPointer()), client);
        auto t2 = clk::now();
        d = us(t2 - t1);
        return (long)b.GetSize();
    });
    if (!(client == S.back())) r.note += "; ROUNDTRIP MISMATCH";
    return r;
}

int main(int argc, char** argv) {
    if (argc < 6) {
        std::cerr << "usage: bench CORPUS.jsonl REPEATS OUT.csv TRACE_LABEL PERIOD_S\n";
        return 2;
    }
    R = std::stoi(argv[2]);
    std::ifstream in(argv[1]);
    std::string line;
    while (std::getline(in, line)) {
        json j = json::parse(line);
        D.push_back(j);
        S.push_back(j.get<native::EmcStat>());
    }
    std::cerr << "cpp bench: " << S.size() << " ticks, " << R << " repeats\n";

    Ser jser = [](const json& j) { return as_bytes(j.dump()); };
    Des jdes = [](const std::vector<uint8_t>& b) { return json::parse(b.begin(), b.end()); };
    Ser cser = [](const json& j) { return json::to_cbor(j); };
    Des cdes = [](const std::vector<uint8_t>& b) { return json::from_cbor(b); };
    Ser mser = [](const json& j) { return json::to_msgpack(j); };
    Des mdes = [](const std::vector<uint8_t>& b) { return json::from_msgpack(b); };

    std::vector<Row> rows;
    rows.push_back(full_dom("nlohmann", "json_full", jser, jdes));
    rows.push_back(patch_dom("nlohmann", "json_merge_patch", jser, jdes, 0));
    rows.push_back(full_dom("nlohmann", "cbor_full", cser, cdes));
    rows.push_back(patch_dom("nlohmann", "cbor_merge_patch", cser, cdes, 0));
    rows.push_back(full_dom("nlohmann", "msgpack_full", mser, mdes));
    rows.push_back(patch_dom("nlohmann", "msgpack_merge_patch", mser, mdes, 0));
    rows.push_back(patch_dom("nlohmann", "json_merge_patch_objidx_structs", jser, jdes, 1));
    rows.push_back(patch_dom("nlohmann", "json_merge_patch_objidx_all", jser, jdes, 2));
    rows.push_back(fb_full());
    rows.push_back(fb_delta());
    rows.push_back(json_read5());
    rows.push_back(fb_read5());

    FILE* f = fopen(argv[3], "w");
    fprintf(f, "side,lib,variant,trace,period_s,ticks,msgs,empty_pct,bytes_mean,bytes_p50,bytes_p95,"
               "bytes_max,enc_med_us,enc_p95_us,dec_med_us,dec_p95_us,diff_med_us,diff_p95_us,"
               "apply_med_us,apply_p95_us,cold_enc_us,cold_dec_us,repeats,note\n");
    for (auto& r : rows) {
        double empty = r.ticks ? 100.0 * (double)(r.ticks - 1 - r.msgs) / (double)(r.ticks - 1) : 0;
        if (r.variant.find("full") != std::string::npos) empty = 0;
        fprintf(f, "cpp,%s,%s,%s,%s,%zu,%zu,%.1f,%.0f,%.0f,%.0f,%.0f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%d,\"%s\"\n",
                r.lib.c_str(), r.variant.c_str(), argv[4], argv[5], r.ticks, r.msgs, empty,
                mean(r.bytes), pct(r.bytes, 0.5), pct(r.bytes, 0.95),
                r.bytes.empty() ? 0 : *std::max_element(r.bytes.begin(), r.bytes.end()),
                pct(r.enc, 0.5), pct(r.enc, 0.95), pct(r.dec, 0.5), pct(r.dec, 0.95),
                pct(r.diff, 0.5), pct(r.diff, 0.95), pct(r.apply, 0.5), pct(r.apply, 0.95),
                r.cold_enc, r.cold_dec, R, r.note.c_str());
        std::cerr << r.variant << " " << r.note << "\n";
    }
    fclose(f);
    return 0;
}
