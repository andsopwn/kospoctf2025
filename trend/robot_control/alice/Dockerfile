FROM ubuntu:20.04

RUN apt-get update -y && apt-get install -y software-properties-common
RUN add-apt-repository universe
RUN apt-get update -y && apt-get install -y xinetd socat python3 python3-pip

RUN mkdir /home/crypto
RUN useradd -d /home/crypto crypto -s /bin/bash
RUN chown -R crypto:crypto /home/crypto

WORKDIR /home/crypto

CMD chown -R root:crypto /home/crypto
RUN chmod 750 /home/crypto

ADD ./requirements.txt /home/crypto/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

ADD ./app.py /home/crypto/app.py
RUN chmod +x /home/crypto/app.py

ADD ./util.py /home/crypto/util.py
RUN chmod +x /home/crypto/util.py

ADD pwn.xinetd /etc/xinetd.d/pwn
ADD ./start.sh /
RUN chmod +x /start.sh

CMD ["/usr/sbin/xinetd", "-dontfork"]

