# 分布式 GPU 信息显示系统

使用 http 和 ssh 进行通信的分布式 GPU 信息显示系统
非常非常简陋的版本，有很多的改进空间

## 代码

### server

+ 服务端代码，基于 flask + mysql
+ 前端使用 echarts 做性能图
+ 使用 pip install -r requirements 安装依赖包

### controller

+ 需要在本地安装 expect 进行 ssh 交互
+ GPU 服务器的信息存在 servers 中
+ 需要新增的用户的信息存在 users 中

### reporter

+ 发送 GPU 状态信息给中心服务器
+ 兼容 python2 和 python3，不需要额外安装 Python 包
+ 启动参数是中心服务器的 ip 地址

## 改进方向

+ 提高传输速度和获取显卡信息的速度
+ 更详细地展示同一张 GPU 上不同用户的使用情况
