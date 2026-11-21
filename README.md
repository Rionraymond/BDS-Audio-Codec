BDS Audio Codec — Web Edition

Bipolar Digital Stream · Browser-Based Audio Codec

BDS Web Codec is an experimental browser-based implementation of the BDS audio format.

Built with HTML, CSS, and JavaScript, it provides a complete experimental workflow for encoding WAV audio into BDS, decoding BDS files back into WAV, playing BDS audio directly in the browser, and inspecting BDS container information.

All audio processing is performed locally in the browser. No server upload is required.

---

Features

1. Audio Encoder

Convert WAV audio into BDS format.

Supported input:

- WAV RIFF
- PCM integer
- Stereo
- 48,000 Hz
- 16-bit and 24-bit

Encoding pipeline:

- PCM normalization
- Linear interpolation oversampling
- Second-order error-feedback modulation
- Radix-3 symbol packing
- BDS container generation

Output: ".bds"

2. Audio Decoder

Reconstruct WAV audio from BDS files.

Features:

- BDS1 container validation
- Metadata parsing
- CRC32 integrity verification
- Radix-3 unpacking
- FIR-based audio reconstruction
- Stereo PCM output

Output: ".wav"

3. BDS Player

Play BDS files directly in the browser without manually exporting a WAV file.

Playback features:

- Load BDS audio
- Play and pause
- Stop playback
- Seek through audio
- Track duration display

The player uses the Web Audio API.

4. BDS Container Analyzer

Inspect BDS files and validate their structure.

Analyzer information:

- Container magic
- Header version
- Sample rate
- Bit depth
- Channel count
- Oversampling ratio
- Frame count
- Payload size
- CRC32 status
- JSON metadata

---

Technical Specifications

Parameter| Web Implementation
Version| 5.1 Prototype
Language| HTML, CSS, JavaScript
Audio Sample Rate| 48,000 Hz
Channels| Stereo
Input Bit Depth| 16-bit / 24-bit
Oversampling| 8×
Internal Rate| 384,000 Hz
Modulator| Second-order error feedback
Oversampling Method| Linear interpolation
Symbol Encoding| Radix-3
Symbol Packing| 5 symbols per byte
Decoder Filter| Blackman-windowed sinc FIR
FIR Taps| 129
Container| BDS1 v1
Integrity Check| CRC32
Playback Engine| Web Audio API

---

BDS Container Format

The web implementation uses the BDS1 container.

Fixed Header

The fixed header occupies 44 bytes.

Offset| Size| Description
0| 4 bytes| Magic identifier: "BDS1"
4| 2 bytes| Container version
6| 2 bytes| Header size
8| 4 bytes| Sample rate
12| 1 byte| Bit depth
13| 1 byte| Channel count
14| 2 bytes| Oversampling ratio
16| 4 bytes| Reserved
20| 8 bytes| Audio frame count
28| 8 bytes| Payload size
36| 4 bytes| CRC32
40| 4 bytes| Metadata size

All multibyte header fields use little-endian byte order.

Metadata

Metadata is stored as UTF-8 encoded JSON immediately after the fixed header.

The maximum metadata size is 1 MiB.

Payload

The payload contains packed ternary symbols.

Each byte stores five ternary digits using radix-3 representation.

Valid packed values range from 0 to 242.

Values from 243 to 255 are invalid.

---

Browser Architecture

The application is divided into five main interfaces:

Interface| Purpose
Encode| WAV to BDS
Decode| BDS to WAV
BDS Player| Direct browser playback
Analyzer| Container inspection
About| Codec information

Processing Architecture

WAV Input
   |
   v
PCM Parsing
   |
   v
Linear Interpolation
   |
   v
Second-Order Modulator
   |
   v
Radix-3 Packing
   |
   v
BDS1 Container

Decoding:

BDS File
   |
   v
Header Validation
   |
   v
Metadata + CRC32
   |
   v
Radix-3 Unpacking
   |
   v
FIR Reconstruction
   |
   v
PCM WAV Output

---

Privacy and Processing

BDS Web Codec operates locally in the browser.

- No audio upload to an external server.
- No backend processing required by the supplied implementation.
- Original files are not modified.
- Playback decoding uses browser memory.

Large audio files may require significant browser RAM.

---

Running the Application

1. Download "bds_audio_codec_v5_2_player.html".
2. Open the HTML file in a modern web browser.
3. Select the desired interface.
4. Load a supported WAV or BDS file.
5. Run the desired operation.

No installation or build process is required for the standalone HTML prototype.

---

Current Limitations

BDS Web Codec is an experimental implementation.

Known limitations:

- Only stereo PCM WAV at 48 kHz is accepted.
- Only 16-bit and 24-bit PCM integer input is supported.
- Oversampling currently uses linear interpolation.
- Audio reconstruction uses a 129-tap FIR filter.
- Large files may consume substantial browser memory.
- Audio quality has not been fully validated against established codecs.
- The implementation is not yet a production-ready game audio format.

---

Future Development

Potential improvements include:

- Improved modulation stability and noise shaping.
- Higher-quality reconstruction filters.
- Reduced memory usage.
- Streaming decoding.
- Web Workers for background processing.
- WebAssembly integration.
- Game engine compatibility.
- Cross-platform format compatibility.

---

Relationship to Native BDS

The Web Edition and Native Edition are separate experimental implementations of the BDS concept.

Their algorithms, filter configurations, and implementation details may differ.

Compatibility should be verified through shared test vectors and cross-implementation validation before either implementation is treated as a universal reference decoder.

---

Project Status

Experimental Prototype — Community Development

BDS Web Codec demonstrates an end-to-end browser workflow for the experimental BDS1 format.

It is intended as a foundation for further research, testing, and development rather than a finalized commercial codec.

BDS Audio Codec — Bipolar Digital Stream.
