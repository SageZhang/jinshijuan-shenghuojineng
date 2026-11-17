#!/usr/bin/env bash
set -euo pipefail

package_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
site_dir=/data/luoyang
backup_root=/data/luoyang-backups

if [ "$(id -u)" -ne 0 ]; then
  echo '请使用 sudo bash deploy.sh 执行。' >&2
  exit 1
fi
cd "$package_dir"
sha256sum -c SHA256SUMS
mkdir -p "$site_dir"
if [ -f "$site_dir/index.html" ]; then
  mkdir -p "$backup_root"
  backup_dir="$(mktemp -d "$backup_root/$(date +%Y%m%d-%H%M%S)-XXXXXX")"
  cp -p -- "$site_dir/index.html" "$backup_dir/index.html"
  printf '旧首页已备份：%s/index.html\n' "$backup_dir"
fi

# Prepare in the destination directory, then atomically replace the homepage.
new_page="$(mktemp "$site_dir/.index-new-XXXXXX")"
trap 'rm -f -- "$new_page"' EXIT
install -m 644 site/index.html "$new_page"
mv -f -- "$new_page" "$site_dir/index.html"
trap - EXIT
echo '已更新 /data/luoyang/index.html。刷新原网站即可，无需重载 Nginx。'
