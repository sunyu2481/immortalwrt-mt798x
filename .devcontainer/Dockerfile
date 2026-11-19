FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        antlr3 asciidoc autoconf automake autopoint bc binutils bison \
        build-essential bzip2 ca-certificates cmake cpio curl \
        device-tree-compiler file flex g++-multilib gawk gcc-multilib \
        gettext git gperf help2man intltool libelf-dev libgmp-dev \
        libmpc-dev libmpfr-dev libncurses5-dev libncursesw5-dev \
        libssl-dev libtool libtool-bin patch pkgconf python3 \
        python3-distutils python3-pyelftools python3-setuptools \
        rsync subversion swig texinfo time unzip wget xsltproc \
        zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
