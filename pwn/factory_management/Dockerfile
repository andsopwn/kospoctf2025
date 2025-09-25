FROM ubuntu:24.04@sha256:b59d21599a2b151e23eea5f6602f4af4d7d31c4e236d22bf0b62b86d2e386b8f

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y socat wget tar make build-essential python3 python3-venv python3-pip python3-distlib ninja-build meson pkg-config libglib2.0-dev libpixman-1-dev zlib1g-dev libc6-arm64-cross
ENV TERM=linux

RUN wget https://download.qemu.org/qemu-10.0.3.tar.xz
RUN tar xvf qemu-10.0.3.tar.xz
WORKDIR /qemu-10.0.3

RUN mkdir build-static
WORKDIR ./build-static

RUN PKG_CONFIG="pkg-config --static" \
../configure --target-list=aarch64-linux-user \
             --disable-system --enable-linux-user \
             --static --prefix=/usr/local
RUN make -j`nproc`
RUN make install

RUN groupadd pwn
RUN useradd -g pwn pwn
WORKDIR /home/pwn

ADD prob /home/pwn/
ADD run.sh /home/pwn/
COPY ./flag /home/pwn/

RUN chmod 460 /home/pwn/*
RUN chown pwn:root /home/pwn/*
RUN chmod +x-w /home/pwn/prob
RUN chmod +x-w /home/pwn/run.sh
RUN chmod o-rx *

USER pwn

CMD socat TCP-LISTEN:1337,reuseaddr,fork EXEC:"./run.sh"