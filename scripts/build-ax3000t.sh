#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail

ax3000t_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ax3000t_root"
umask 022

if [ "$(id -u)" -eq 0 ]; then
	printf '%s\n' '请使用普通用户构建固件。' >&2
	exit 1
fi
ax3000t_action=${1:-build}
ax3000t_jobs=${AX3000T_JOBS:-$(nproc)}
if ! [[ "$ax3000t_jobs" =~ ^[1-9][0-9]*$ ]]; then
	printf '%s\n' 'AX3000T_JOBS 必须是正整数。' >&2
	exit 1
fi
if [ "$ax3000t_jobs" -gt 4 ]; then
	ax3000t_jobs=4
fi

finish_image() {
	python3 scripts/ax3000t/check-build.py image
	./scripts/diffconfig.sh > bin/targets/mediatek/mt7981/ax3000t-stock.diffconfig
	git rev-parse HEAD > bin/targets/mediatek/mt7981/ax3000t-source-commit.txt
	cp scripts/ax3000t/feeds.lock.json \
		bin/targets/mediatek/mt7981/ax3000t-feeds.lock.json
	(
		cd bin/targets/mediatek/mt7981
		sha256sum *xiaomi_mi-router-ax3000t-stock-squashfs-sysupgrade.bin \
			> ax3000t-stock.sha256
	)
	printf '%s\n' '构建完成：bin/targets/mediatek/mt7981/'
}

case "$ax3000t_action" in
	prepare)
		python3 scripts/ax3000t/prepare.py
		;;
	check)
		python3 scripts/ax3000t/check-build.py config
		;;
	download)
		python3 scripts/ax3000t/check-build.py config
		make download -j"$ax3000t_jobs"
		;;
	image)
		python3 scripts/ax3000t/check-build.py config
		mkdir -p logs
		make package/install -j1 V=s 2>&1 | tee logs/ax3000t-package-install.log
		make target/install -j"$ax3000t_jobs" V=s 2>&1 | tee logs/ax3000t-image.log
		make package/index -j1 2>&1 | tee logs/ax3000t-package-index.log
		finish_image
		;;
	build)
		if [ "$(uname -m)" != x86_64 ]; then
			printf '%s\n' '完整构建要求 AMD64 主机。' >&2
			exit 1
		fi
		python3 scripts/ax3000t/check-build.py config
		ax3000t_available_kb=$(df -Pk . | awk 'NR == 2 {print $4}')
		if ! compgen -G 'staging_dir/toolchain-*/stamp/.gcc_final_installed' >/dev/null && \
			[ "$ax3000t_available_kb" -lt 26214400 ]; then
			printf '%s\n' '首次完整构建需 25 GiB 可用空间。' >&2
			exit 1
		fi
		mkdir -p logs
		make download -j"$ax3000t_jobs" 2>&1 | tee logs/ax3000t-download.log
		if ! make -j"$ax3000t_jobs" 2>&1 | tee logs/ax3000t-build.log; then
			printf '%s\n' '并行构建失败，使用单线程输出详细错误。'
			make -j1 V=s 2>&1 | tee logs/ax3000t-build-verbose.log
		fi
		finish_image
		;;
	*)
		printf '%s\n' '用法：build-ax3000t.sh prepare|check|download|build|image' >&2
		exit 1
		;;
esac
