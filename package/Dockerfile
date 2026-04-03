FROM python:3.13.12-bookworm

RUN pip install pyinstaller
RUN pip install pyudev
RUN pip install pathspec
RUN pip install pydbus

WORKDIR /build

CMD pyinstaller borXplo.spec
