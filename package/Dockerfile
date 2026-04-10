FROM python:3.13.12-bookworm

RUN pip install pyinstaller
RUN pip install pyudev

WORKDIR /build

CMD pyinstaller borXplo.spec
