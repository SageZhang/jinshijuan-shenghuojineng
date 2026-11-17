# 苍生铸世资料片专题站 | 金石卷 · 更新部署

本包包含副本攻略、TN速查、DPS技改、宏与循环、木桩观察和23个DPS详情页，共28个内嵌视图。总入口已命名为 site/index.html，页面内容、样式和脚本均内置；服务器无需 Node.js 或数据库。来源与视频链接需联网。

## 2026-10-03 更新范围

- 全部23份DPS手册完成资料核对：19份体服试用、4份旧版待复测，61段宏保留来源原文。
- 25人普通五首领更新水幕、大圈、炸弹分配、二号剑位置及同圈叠层规则；10人复查后保留原证据日期。
- 25人英雄新增独立入口，公开攻略正文尚未核实，页面明确为“资料待核”，不包含普通难度复制出的英雄机制。
- TN资料仍截至9月15日；木桩视频仍是9月16日历史样本，不能作为二改强度排行。

## 更新现有阿里云网站

现有网站目录为 /data/luoyang，沿用原域名、HTTPS及Nginx配置。
将 cangsheng-deploy.tar.gz 上传到服务器 /home/cangsheng-deploy.tar.gz，然后执行。命令也兼容放在当前登录用户主目录（$HOME）中的安装包：

```bash
(
  set -e
  archive_path=/home/cangsheng-deploy.tar.gz
  [ -f "$archive_path" ] || archive_path="$HOME/cangsheng-deploy.tar.gz"
  [ -f "$archive_path" ] || { echo '未在 /home 或当前用户主目录找到安装包。' >&2; exit 1; }
  package_dir=$(mktemp -d /tmp/cangsheng-deploy.XXXXXX)
  tar -xzf "$archive_path" -C "$package_dir"
  sudo bash "$package_dir/deploy.sh"
)
```

`/tmp` 仅用于新建临时解压目录，安装包从 Home 位置读取。脚本先校验SHA256，将旧首页备份至 /data/luoyang-backups/时间-随机字符/index.html，再替换 /data/luoyang/index.html。其他网站文件及Nginx配置保持原样。刷新原网址即可，无需重启或重载Nginx；若仍显示旧页，使用Ctrl+F5。若域名配置了CDN，请刷新首页缓存。

备份路径会在命令输出中显示。需要恢复时，将对应备份的 index.html 复制回 /data/luoyang/index.html。

## ZIP方式

cangsheng-deploy.zip 与tar.gz内容一致，任选一个即可。上传至 /home/cangsheng-deploy.zip 或当前登录用户主目录后执行：

```bash
(
  set -e
  archive_path=/home/cangsheng-deploy.zip
  [ -f "$archive_path" ] || archive_path="$HOME/cangsheng-deploy.zip"
  [ -f "$archive_path" ] || { echo '未在 /home 或当前用户主目录找到安装包。' >&2; exit 1; }
  package_dir=$(mktemp -d /tmp/cangsheng-deploy.XXXXXX)
  unzip "$archive_path" -d "$package_dir"
  sudo bash "$package_dir/deploy.sh"
)
```

也可在本机解压ZIP，用服务器面板将 site/index.html 上传覆盖 /data/luoyang/index.html，覆盖前自行备份旧文件。

## 包内文件

- site/index.html：完整专题站首页
- deploy.sh：校验、备份及替换脚本
- README-deploy.md：本说明
- SHA256SUMS：首页校验值

默认首页包含顶部栏目导航。25人总表链接格式为 https://你的域名/#raid~skill-table%3Fdifficulty%3D25-normal 。页面使用#路由，无需新增反向代理或路径重写。

打包日期为2026-10-03；页面内各栏目保留实际资料核对日期。名单保存在访问者浏览器中，继续使用同一域名与协议可沿用原存储。
