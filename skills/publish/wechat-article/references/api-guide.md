# 微信公众号 API 指南

## 接口列表

### 1. 获取 Access Token
```
GET https://api.weixin.qq.com/cgi-bin/token
?grant_type=client_credential
&appid=APPID
&secret=APPSECRET
```

### 2. 上传永久素材
```
POST https://api.weixin.qq.com/cgi-bin/material/add_material
?access_token=ACCESS_TOKEN
&type=image

Content-Type: multipart/form-data
Body: media=图片文件
```

### 3. 创建草稿
```
POST https://api.weixin.qq.com/cgi-bin/draft/add
?access_token=ACCESS_TOKEN

{
  "articles": [{
    "title": "标题",
    "author": "作者",
    "digest": "摘要",
    "content": "HTML内容",
    "thumb_media_id": "封面素材ID",
    "show_cover_pic": 1,
    "need_open_comment": 1
  }]
}
```

## 注意事项

1. **永久素材 vs 临时素材**
   - 草稿必须使用永久素材的 media_id
   - 临时素材（media/upload）无效

2. **IP 白名单**
   - 必须在公众号后台配置服务器 IP

3. **账号类型**
   - 订阅号需要认证才能使用部分接口
   - 服务号权限更完整

## 错误码

| 错误码 | 含义 | 解决 |
|--------|------|------|
| 40007 | invalid media_id | 使用永久素材 |
| 48001 | api unauthorized | 检查账号权限 |
| 42001 | access_token expired | 重新获取 token |
