# TeleDL
[博客地址](https://blog.csdn.net/qq_40933467/article/details/113867758?spm=1001.2014.3001.5501)


#### 使用说明：
Telegram 频道/群组 文件下载脚本

脚本需要python3环境，具体安装教程自行搜索。

测试环境  Ubuntu 18.04.5 LTS & Python 3.6.9

**1. 前提**
  
 - 从 https://my.telegram.org/apps 获取自己的Telegram API密钥。

 - 下载脚本
 ```
 git clone https://github.com/monicedy/TeleDL.git
 ```

**2. 使用**

 - 进入脚本目录
 ```
 cd TeleDL
 ```
 - 安装依赖`pip install telethon`, 缺啥补啥

 - 修改teledl.py文件内的 api_id 和 api_hash 为你自己的

 - 修改脚本内的频道名称、保存路径、 bot_token 、 admin_id 、 chat 等必填配置
   
 - 运行  
 ```
 python3 teledl.py
 ```
 - 按照提示输入telegram绑定的手机号获取验证码并输入
 
 - 配置完成后需要给bot发送 /start 频道的链接 0 才会正式开始运行脚本，否则无法启动 0代表开始下载消息的ID，可以自行修改。
 

