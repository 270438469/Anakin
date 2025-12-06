Anakin

本项目提供一个用于监控指定钱包地址的 Python 脚本。
你可以为每个地址配置标签，方便在日志中区分不同监控对象。

一、项目说明

主脚本：auto_monitor_byanankin.py

功能：监控指定钱包地址的行为，并通过标签进行标识。

运行方式：

python auto_monitor_byanankin.py

二、运行环境

Python 版本：3.11

安装依赖：

pip install hyperliquid-monitor

三、地址与标签配置

在脚本中通过 LABELS 字典配置需要监控的钱包地址及其标签。

1. 当前默认监控地址
LABELS = {
    "0xdAe4DF7207feB3B350e4284C8eFe5f7DAc37f637": "魏神",
    "0x4aab8988462923ca3cbaa7e94df0cc523817cd64": "hype聪明钱"
}

2. 如何新增地址与标签

在 LABELS 字典中添加新条目，格式为：

"钱包地址": "标签"


示例：新增一个地址

LABELS = {
    "0xdAe4DF7207feB3B350e4284C8eFe5f7DAc37f637": "魏神",
    "0x4aab8988462923ca3cbaa7e94df0cc523817cd64": "hype聪明钱",
    "0x1234567890abcdef1234567890abcdef12345678": "新地址标签"
}


保存文件后，重新运行脚本即可，监控器会自动加载所有地址（无需修改其他代码）。

移除地址只需从 LABELS 字典中删除对应条目。

四、快速开始

安装依赖：

pip install hyperliquid-monitor


编辑脚本中的 LABELS 字典，配置你要监控的钱包地址和标签。

启动监控脚本：

python auto_monitor_byanankin.py


在终端日志中查看不同地址的监控输出，标签将帮助你区分不同的钱包角色（如“魏神”、“hype聪明钱”等）。
