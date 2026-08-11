# Builder image for ClarityOS Desktop.
#
# Deliberately unprivileged: images are assembled with mke2fs -d (populate ext4 from a
# directory), mtools (populate FAT), and sfdisk against a plain file. No loop devices, so
# this needs neither --privileged nor /dev/loop access.

# ---------------------------------------------------------------------------
# Stage 1: compile llama.cpp once, so it is cached across image builds.
# ---------------------------------------------------------------------------
FROM alpine:3.21 AS llama

ARG LLAMA_REF=b4585

RUN apk add --no-cache build-base cmake git linux-headers openblas-dev

WORKDIR /src
RUN git clone --depth 1 --branch "${LLAMA_REF}" https://github.com/ggerganov/llama.cpp.git . \
 || git clone --depth 1 https://github.com/ggerganov/llama.cpp.git .

# GGML_NATIVE=OFF keeps the binary off -march=native so it is not pinned to this build host.
# AVX2/FMA/F16C are enabled explicitly: every Haswell-or-later CPU (2013+) has them, which
# covers any desktop we care about, and they are worth a large factor on CPU inference.
RUN cmake -B build \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=OFF \
      -DLLAMA_CURL=OFF \
      -DGGML_NATIVE=OFF \
      -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON \
 && cmake --build build --config Release -j"$(nproc)" --target llama-server llama-cli \
 && mkdir -p /llama/bin \
 && find build -type f \( -name 'llama-server' -o -name 'llama-cli' \) -exec cp {} /llama/bin/ \; \
 && strip /llama/bin/* || true

# ---------------------------------------------------------------------------
# Stage 2: the image-assembly toolchain.
# ---------------------------------------------------------------------------
FROM alpine:3.21

RUN apk add --no-cache \
      bash curl \
      e2fsprogs e2fsprogs-extra \
      dosfstools mtools sfdisk util-linux \
      grub grub-efi \
      qemu-img xz coreutils findutils

# mtools refuses to touch plain image files without this.
RUN printf 'mtools_skip_check=1\n' > /etc/mtools.conf

COPY --from=llama /llama/bin/ /opt/llama/bin/

WORKDIR /build
COPY build.sh /usr/local/bin/build.sh
RUN chmod +x /usr/local/bin/build.sh
ENTRYPOINT ["/usr/local/bin/build.sh"]
