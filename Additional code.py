
import math
import time

# ============================================================
# BDS AUDIO ANALYZER v4.1
# Correct Oversampling + Radix-3 + Polyphase FIR
# ============================================================

VERSION = "4.1"

SAMPLE_RATE = 8000
DURATION = 1.0
OSR = 8

FREQUENCIES = [
    100, 250, 500, 750,
    1000, 1500, 2000, 3000, 3500
]

FIR_TAPS = [129, 257, 513]
FIR_CUTOFFS = [0.05625, 0.05875]

GAIN_ERROR_LIMIT = 6.0


# ============================================================
# SIGNAL GENERATION
# ============================================================

def generate_signal(frequency):
    count = int(SAMPLE_RATE * DURATION)

    return [
        0.5 * math.sin(
            2.0 * math.pi * frequency * i / SAMPLE_RATE
        )
        for i in range(count)
    ]


# ============================================================
# 8X LINEAR INTERPOLATION
# ============================================================

def oversample_linear(audio, factor):
    if not audio:
        raise ValueError("Input audio kosong.")

    output = []
    count = len(audio)

    for i in range(count):
        current = audio[i]

        if i + 1 < count:
            following = audio[i + 1]
        else:
            following = current

        for phase in range(factor):
            fraction = phase / factor

            value = (
                current * (1.0 - fraction)
                + following * fraction
            )

            output.append(value)

    expected = len(audio) * factor

    if len(output) != expected:
        raise RuntimeError("Kesalahan jumlah sampel oversampling.")

    return output


# ============================================================
# BDS SECOND-ORDER ERROR FEEDBACK MODULATOR
# ============================================================

def bds_encode(audio):
    symbols = []

    error_1 = 0.0
    error_2 = 0.0
    max_state = 0.0

    for sample in audio:
        value = sample + 2.0 * error_1 - error_2

        max_state = max(max_state, abs(value))

        if value > 0.5:
            symbol = 1
        elif value < -0.5:
            symbol = -1
        else:
            symbol = 0

        error = value - symbol

        error_2 = error_1
        error_1 = error

        symbols.append(symbol)

    return symbols, max_state


# ============================================================
# RADIX-3 PACKING
#
# -1 -> 0
#  0 -> 1
# +1 -> 2
#
# Five ternary symbols fit in one byte.
# ============================================================

def radix3_pack(symbols):
    packed = []

    for start in range(0, len(symbols), 5):
        group = symbols[start:start + 5]

        value = 0
        multiplier = 1

        for symbol in group:
            if symbol == -1:
                digit = 0
            elif symbol == 0:
                digit = 1
            elif symbol == 1:
                digit = 2
            else:
                raise ValueError("Simbol BDS tidak valid.")

            value += digit * multiplier
            multiplier *= 3

        # Padding menggunakan simbol 0 (digit 1).
        while len(group) < 5:
            value += multiplier
            multiplier *= 3
            group.append(0)

        if value > 242:
            raise RuntimeError("Nilai Radix-3 tidak valid.")

        packed.append(value)

    return bytes(packed)


def radix3_unpack(data, original_count):
    symbols = []

    for byte in data:
        if byte > 242:
            raise ValueError("Byte Radix-3 tidak valid.")

        value = byte

        for _ in range(5):
            digit = value % 3
            value //= 3

            if digit == 0:
                symbols.append(-1)
            elif digit == 1:
                symbols.append(0)
            else:
                symbols.append(1)

    if len(symbols) < original_count:
        raise ValueError("Data simbol tidak lengkap.")

    return symbols[:original_count]


# ============================================================
# BLACKMAN-WINDOWED SINC FIR
# ============================================================

def design_fir(taps, cutoff):
    if taps < 3 or taps % 2 == 0:
        raise ValueError("Jumlah tap harus ganjil.")

    if not 0.0 < cutoff < 0.5:
        raise ValueError("Cutoff harus berada antara 0 dan 0.5.")

    middle = taps // 2
    coefficients = []

    for n in range(taps):
        x = n - middle

        if x == 0:
            sinc = 2.0 * cutoff
        else:
            sinc = (
                math.sin(2.0 * math.pi * cutoff * x)
                / (math.pi * x)
            )

        window = (
            0.42
            - 0.5 * math.cos(2.0 * math.pi * n / (taps - 1))
            + 0.08 * math.cos(4.0 * math.pi * n / (taps - 1))
        )

        coefficients.append(sinc * window)

    total = sum(coefficients)

    if abs(total) < 1e-15:
        raise RuntimeError("Normalisasi FIR gagal.")

    return [value / total for value in coefficients]


# ============================================================
# POLYPHASE FIR DECIMATION
# Calculates only samples that survive decimation.
# ============================================================

def polyphase_decimate(symbols, coefficients, factor):
    taps = len(coefficients)
    middle = taps // 2

    if len(symbols) % factor != 0:
        raise ValueError("Panjang simbol tidak sesuai OSR.")

    output_count = len(symbols) // factor
    output = [0.0] * output_count

    source_length = len(symbols)

    for m in range(output_count):
        center = m * factor
        value = 0.0

        for j, coefficient in enumerate(coefficients):
            index = center + j - middle

            if index < 0:
                index = 0
            elif index >= source_length:
                index = source_length - 1

            value += symbols[index] * coefficient

        output[m] = value

    return output


# ============================================================
# METRICS
# ============================================================

def validate_lengths(original, decoded):
    if len(original) != len(decoded):
        raise ValueError(
            "Panjang data berbeda: "
            + str(len(original))
            + " vs "
            + str(len(decoded))
        )


def metric_range(length, taps):
    # Mengabaikan area transien di kedua ujung sinyal.
    margin = (taps // 2) // OSR + 2

    if length <= margin * 2:
        raise ValueError("Data terlalu pendek untuk evaluasi.")

    return margin, length - margin


def calculate_snr(original, decoded, taps):
    validate_lengths(original, decoded)

    start, end = metric_range(len(original), taps)

    signal_power = 0.0
    noise_power = 0.0

    for i in range(start, end):
        reference = original[i]
        error = reference - decoded[i]

        signal_power += reference * reference
        noise_power += error * error

    if noise_power <= 1e-30:
        return float("inf")

    if signal_power <= 1e-30:
        return float("-inf")

    return 10.0 * math.log10(
        signal_power / noise_power
    )


def calculate_rmse(original, decoded, taps):
    validate_lengths(original, decoded)

    start, end = metric_range(len(original), taps)

    error_power = 0.0

    for i in range(start, end):
        error = original[i] - decoded[i]
        error_power += error * error

    return math.sqrt(error_power / (end - start))


def calculate_peak_error(original, decoded, taps):
    validate_lengths(original, decoded)

    start, end = metric_range(len(original), taps)

    peak = 0.0

    for i in range(start, end):
        error = abs(original[i] - decoded[i])
        peak = max(peak, error)

    return peak


def measure_amplitude(signal, frequency, taps):
    start, end = metric_range(len(signal), taps)

    sine_sum = 0.0
    cosine_sum = 0.0
    count = end - start

    for i in range(start, end):
        angle = (
            2.0 * math.pi
            * frequency
            * i / SAMPLE_RATE
        )

        sine_sum += signal[i] * math.sin(angle)
        cosine_sum += signal[i] * math.cos(angle)

    return 2.0 * math.sqrt(
        sine_sum * sine_sum
        + cosine_sum * cosine_sum
    ) / count


def calculate_gain_error(original, decoded, frequency, taps):
    input_amplitude = measure_amplitude(
        original, frequency, taps
    )

    output_amplitude = measure_amplitude(
        decoded, frequency, taps
    )

    if output_amplitude <= 1e-15:
        return -120.0

    return 20.0 * math.log10(
        output_amplitude / input_amplitude
    )


# ============================================================
# TEST PREPARATION
# ============================================================

def prepare_test(frequency):
    original = generate_signal(frequency)

    high_rate = oversample_linear(original, OSR)

    symbols, max_state = bds_encode(high_rate)

    if len(symbols) != len(original) * OSR:
        raise RuntimeError("Jumlah simbol BDS tidak sesuai.")

    packed = radix3_pack(symbols)

    restored_symbols = radix3_unpack(
        packed, len(symbols)
    )

    if restored_symbols != symbols:
        raise RuntimeError("Verifikasi Radix-3 gagal.")

    return {
        "frequency": frequency,
        "original": original,
        "symbols": restored_symbols,
        "packed": packed,
        "max_state": max_state
    }


# ============================================================
# MAIN ANALYSIS
# ============================================================

def main():
    start_time = time.time()

    print("=" * 58)
    print("             BDS AUDIO ANALYZER v" + VERSION)
    print("       CORRECT OVERSAMPLING + POLYPHASE FIR")
    print("=" * 58)

    print("\nOSR:", OSR)
    print("Sample rate:", SAMPLE_RATE, "Hz")
    print("Frequencies:", len(FREQUENCIES))
    print("FIR configurations:",
          len(FIR_TAPS) * len(FIR_CUTOFFS))

    print("\nPreparing signals...")

    prepared = []

    for frequency in FREQUENCIES:
        test = prepare_test(frequency)
        prepared.append(test)

        print(
            str(frequency).rjust(5),
            "Hz | Symbols:",
            len(test["symbols"]),
            "| Packed:",
            len(test["packed"]),
            "bytes | Max state:",
            round(test["max_state"], 4)
        )

    # Pastikan panjang semua sinyal benar.
    for test in prepared:
        expected = len(test["original"]) * OSR

        if len(test["symbols"]) != expected:
            raise RuntimeError("Validasi simbol gagal.")

    print("\n" + "=" * 58)
    print("              FIR CONFIGURATION TEST")
    print("=" * 58)

    results = []

    for taps in FIR_TAPS:
        for cutoff in FIR_CUTOFFS:

            coefficients = design_fir(taps, cutoff)

            snr_values = []
            gain_errors = []

            print(
                "\nTesting:",
                taps,
                "taps | cutoff:",
                cutoff
            )

            for test in prepared:
                decoded = polyphase_decimate(
                    test["symbols"],
                    coefficients,
                    OSR
                )

                original = test["original"]

                # Pemeriksaan ketat sebelum pengukuran.
                validate_lengths(original, decoded)

                snr = calculate_snr(
                    original, decoded, taps
                )

                gain = calculate_gain_error(
                    original,
                    decoded,
                    test["frequency"],
                    taps
                )

                snr_values.append(snr)
                gain_errors.append(abs(gain))

                print(
                    str(test["frequency"]).rjust(5),
                    "Hz | SNR:",
                    round(snr, 2),
                    "dB | Gain:",
                    round(gain, 2),
                    "dB"
                )

            average_snr = sum(snr_values) / len(snr_values)
            average_gain_error = (
                sum(gain_errors) / len(gain_errors)
            )
            worst_gain_error = max(gain_errors)

            result = {
                "taps": taps,
                "cutoff": cutoff,
                "average_snr": average_snr,
                "average_gain_error": average_gain_error,
                "worst_gain_error": worst_gain_error
            }

            results.append(result)

            print("Average SNR:",
                  round(average_snr, 2), "dB")

            print("Average gain error:",
                  round(average_gain_error, 2), "dB")

            print("Worst gain error:",
                  round(worst_gain_error, 2), "dB")

    # ========================================================
    # OPTIMIZER
    # ========================================================

    print("\n" + "=" * 58)
    print("                 FIR OPTIMIZER")
    print("=" * 58)

    eligible = [
        result for result in results
        if result["worst_gain_error"] <= GAIN_ERROR_LIMIT
    ]

    if not eligible:
        print("Tidak ada konfigurasi yang memenuhi batas gain.")
        print("Gunakan hasil terbaik berdasarkan gain error.")

        eligible = sorted(
            results,
            key=lambda item: item["worst_gain_error"]
        )[:1]

    selected = max(
        eligible,
        key=lambda item: item["average_snr"]
    )

    print("\nSelected configuration:")
    print("FIR taps:", selected["taps"])
    print("Cutoff:", selected["cutoff"])
    print("Average SNR:",
          round(selected["average_snr"], 2), "dB")
    print("Average gain error:",
          round(selected["average_gain_error"], 2), "dB")
    print("Worst gain error:",
          round(selected["worst_gain_error"], 2), "dB")

    # ========================================================
    # FINAL QUALITY REPORT
    # ========================================================

    coefficients = design_fir(
        selected["taps"],
        selected["cutoff"]
    )

    print("\n" + "=" * 58)
    print("              FINAL QUALITY REPORT")
    print("=" * 58)

    for test in prepared:
        decoded = polyphase_decimate(
            test["symbols"],
            coefficients,
            OSR
        )

        original = test["original"]

        validate_lengths(original, decoded)

        snr = calculate_snr(
            original, decoded, selected["taps"]
        )

        rmse = calculate_rmse(
            original, decoded, selected["taps"]
        )

        peak = calculate_peak_error(
            original, decoded, selected["taps"]
        )

        gain = calculate_gain_error(
            original,
            decoded,
            test["frequency"],
            selected["taps"]
        )

        print("\nFrequency:", test["frequency"], "Hz")
        print("Original samples:", len(original))
        print("BDS symbols:", len(test["symbols"]))
        print("Decoded samples:", len(decoded))
        print("SNR:", round(snr, 2), "dB")
        print("RMSE:", round(rmse, 7))
        print("Peak error:", round(peak, 7))
        print("Gain:", round(gain, 2), "dB")

    elapsed = time.time() - start_time

    print("\n" + "=" * 58)
    print("Elapsed time:", round(elapsed, 2), "seconds")
    print("BDS v" + VERSION + " analysis completed.")
    print("=" * 58)


if __name__ == "__main__":
    main()
