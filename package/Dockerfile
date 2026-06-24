FROM python:3.13-bookworm

RUN pip install pyinstaller
RUN pip install pyudev
RUN pip install beartype

WORKDIR /build

CMD pyinstaller borXplo.spec -y
