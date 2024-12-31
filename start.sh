#!/bin/sh

# 運行數據庫遷移
flask db upgrade

# 啟動 edutalk
edutalk -c /edutalk/edutalk.ini start