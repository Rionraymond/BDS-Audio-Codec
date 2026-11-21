#!/usr/bin/env python3
"""
BDS experimental audio codec — prototype v0.1
Bipolar ternary stream:
    10 = +1
    00 =  0
    01 = -1
    11 = reserved/invalid

This is an educational first-order ternary delta-sigma prototype, not a
production codec and not a claim of better quality than PCM/DSD.

Dependencies:
    pip install numpy scipy soundfile

Usage:
    python bds.py encode input.wav output.bds --osr 16
    python bds.py decode input.bds output.wav
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

MAGIC = b"BDS1"
VERSION = 1
# magic, version, source sample rate, channels, oversampling ratio, frames
HEADER = struct.Struct(">4sBIBHQ")

# Symbol mapping to two-bit codes:
# 0 -> 00, -1 -> 01, +1 -> 10. Code 11 is reserved.
SYMBOL_TO_CODE = {0: 0, -1: 1, 1: 2}
CODE_TO_SYMBOL = np.array([0, -1, 1, 0], dtype=np.int8)


def ternary_delta_sigma(x: np.ndarray) -> np.ndarray:
    """First-order error-feedback ternary modulator for one channel.

    x must be a finite float array approximately within [-1, 1].
    Quantizer thresholds are +/-0.5; output levels are {-1, 0, +1}.
    """
    out = np.empty(x.size, dtype=np.int8)
    error = 0.0

    for i, sample in enumerate(x):
        v = float(sample) + error
        if v > 0.5:
            q = 1
        elif v < -0.5:
            q = -1
        else:
            q = 0

        out[i] = q
        error = v - q

    return out


def pack_symbols(symbols: np.ndarray) -> bytes:
    """Pack four ternary symbols into each byte, 2 bits per symbol."""
    symbols = np.asarray(symbols, dtype=np.int8).reshape(-1)
    codes = np.empty(symbols.size, dtype=np.uint8)

    codes[symbols == 0] = 0
    codes[symbols == -1] = 1
    codes[symbols == 1] = 2

    if np.any((symbols < -1) | (symbols > 1)):
        raise ValueError("Ternary symbols must be -1, 0, or +1.")

    pad = (-codes.size) % 4
    if pad:
        codes = np.pad(codes, (0, pad), constant_values=0)

    groups = codes.reshape(-1, 4)
    packed = (
        (groups[:, 0] << 6)
        | (groups[:, 1] << 4)
        | (groups[:, 2] << 2)
        | groups[:, 3]
    )
    return packed.tobytes()


def unpack_symbols(payload: bytes, count: int) -> np.ndarray:
    """Unpack exactly count symbols from packed 2-bit data."""
    raw = np.frombuffer(payload, dtype=np.uint8)
    codes = np.empty(raw.size * 4, dtype=np.uint8)
    codes[0::4] = (raw >> 6) & 0x03
    codes[1::4] = (raw >> 4) & 0x03
    codes[2::4] = (raw >> 2) & 0x03
    codes[3::4] = raw & 0x03

    codes = codes[:count]
    if np.any(codes == 3):
        raise ValueError("Reserved symbol code 11 found in BDS payload.")
    return CODE_TO_SYMBOL[codes]


def encode_wav(input_path: str, output_path: str, osr: int = 16) -> None:
    audio, sample_rate = sf.read(input_path, dtype="float32", always_2d=True)
    if not np.all(np.isfinite(audio)):
        raise ValueError("Input WAV contains NaN or infinite samples.")
    if osr < 2:
        raise ValueError("Oversampling ratio must be at least 2.")

    frames, channels = audio.shape
    # Keep headroom to avoid overloading the modulator on full-scale peaks.
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.999:
        audio = audio * (0.999 / peak)

    streams = []
    for ch in range(channels):
        high_rate = resample_poly(audio[:, ch], osr, 1).astype(np.float32)
        streams.append(ternary_delta_sigma(high_rate))

    # Interleave channels frame-by-frame at the high sample rate.
    symbols = np.stack(streams, axis=1).reshape(-1)
    payload = pack_symbols(symbols)

    header = HEADER.pack(
        MAGIC, VERSION, int(sample_rate), int(channels), int(osr), int(frames)
    )
    Path(output_path).write_bytes(header + payload)

    bit_rate = sample_rate * osr * channels * 2
    print(f"Encoded: {input_path} -> {output_path}")
    print(f"Source: {sample_rate} Hz, {channels} channel(s), {frames} frames")
    print(f"BDS stream: {sample_rate * osr} symbols/s/channel, 2 bits/symbol")
    print(f"Raw stream rate: {bit_rate:,} bit/s (before file header)")
    print(f"File size: {Path(output_path).stat().st_size:,} bytes")


def decode_bds(input_path: str, output_path: str) -> None:
    data = Path(input_path).read_bytes()
    if len(data) < HEADER.size:
        raise ValueError("File is too small to contain a BDS header.")

    magic, version, sample_rate, channels, osr, frames = HEADER.unpack_from(data)
    if magic != MAGIC:
        raise ValueError("Not a BDS file (magic signature mismatch).")
    if version != VERSION:
        raise ValueError(f"Unsupported BDS version: {version}")
    if channels < 1 or osr < 2:
        raise ValueError("Invalid channel count or oversampling ratio.")

    symbol_count = frames * osr * channels
    payload = data[HEADER.size:]
    expected_bytes = (symbol_count + 3) // 4
    if len(payload) != expected_bytes:
        raise ValueError(
            f"Payload length mismatch: expected {expected_bytes} bytes, "
            f"found {len(payload)}."
        )

    symbols = unpack_symbols(payload, symbol_count)
    high_rate = symbols.reshape(frames * osr, channels).astype(np.float32)

    decoded = np.empty((frames, channels), dtype=np.float32)
    for ch in range(channels):
        # resample_poly applies a reconstruction low-pass filter before
        # decimation. This is a basic prototype filter, not optimized mastering.
        channel_audio = resample_poly(high_rate[:, ch], 1, osr)
        if channel_audio.size < frames:
            channel_audio = np.pad(channel_audio, (0, frames - channel_audio.size))
        decoded[:, ch] = channel_audio[:frames]

    decoded = np.clip(decoded, -1.0, 1.0)
    sf.write(output_path, decoded, sample_rate, subtype="PCM_24")
    print(f"Decoded: {input_path} -> {output_path}")
    print(f"Output: {sample_rate} Hz, {channels} channel(s), {frames} frames")


def main() -> None:
    parser = argparse.ArgumentParser(description="Experimental BDS ternary audio codec")
    sub = parser.add_subparsers(dest="command", required=True)

    enc = sub.add_parser("encode", help="Encode WAV to BDS")
    enc.add_argument("input")
    enc.add_argument("output")
    enc.add_argument("--osr", type=int, default=16,
                     help="Oversampling ratio (default: 16; try 64 for experiments)")

    dec = sub.add_parser("decode", help="Decode BDS to WAV")
    dec.add_argument("input")
    dec.add_argument("output")

    args = parser.parse_args()
    if args.command == "encode":
        encode_wav(args.input, args.output, args.osr)
    else:
        decode_bds(args.input, args.output)


if __name__ == "__main__":
    main()
