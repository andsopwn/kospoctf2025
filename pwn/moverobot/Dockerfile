FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    socat \
    && rm -rf /var/lib/apt/lists/*


RUN useradd -m ctf


COPY prob /home/ctf/prob
COPY flag /flag


RUN chmod 644 /flag
RUN chmod +x /home/ctf/prob
RUN chown root:ctf /home/ctf/prob


USER ctf
WORKDIR /home/ctf


CMD ["socat", "TCP-LISTEN:8400,reuseaddr,fork", "EXEC:./prob"] 