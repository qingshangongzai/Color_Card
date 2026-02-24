# Color Card 官网部署指南

## 方法一：使用 GitHub Pages（推荐）

### 步骤 1：创建 GitHub 仓库

1. 打开 https://github.com/new
2. 仓库名称填写：`color-card-website`（或其他你喜欢的名字）
3. 选择 **Public**（公开）
4. 点击 **Create repository**

### 步骤 2：上传网站文件

#### 方式 A：使用 Git 命令行（推荐）

```bash
# 进入网站目录
cd website

# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 提交文件
git commit -m "Initial commit: Color Card website"

# 关联远程仓库（将下面的 URL 替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/color-card-website.git

# 推送到 GitHub
git branch -M main
git push -u origin main
```

#### 方式 B：直接上传（更简单）

1. 打开你的 GitHub 仓库页面
2. 点击 **"uploading an existing file"** 链接
3. 将 `website` 文件夹中的所有文件拖拽到页面中
4. 点击 **Commit changes**

### 步骤 3：启用 GitHub Pages

1. 在 GitHub 仓库页面，点击 **Settings**（设置）
2. 左侧菜单点击 **Pages**
3. **Source** 部分选择 **GitHub Actions**
4. 等待几分钟，网站就会自动部署

### 步骤 4：访问你的网站

部署完成后，你可以通过以下地址访问：

```
https://你的用户名.github.io/color_card/
```

例如：`https://qingshangongzai.github.io/color_card/`

---

## 方法二：使用 Gitee Pages（国内访问更快）

### 步骤 1：创建 Gitee 仓库

1. 打开 https://gitee.com/new
2. 仓库名称填写：`color-card-website`
3. 选择 **公开**
4. 点击 **创建**

### 步骤 2：上传文件

和方法一的步骤 2 相同，只是将 GitHub 地址换成 Gitee 地址：

```bash
git remote add origin https://gitee.com/你的用户名/color-card-website.git
```

### 步骤 3：启用 Gitee Pages

1. 在 Gitee 仓库页面，点击 **服务** → **Gitee Pages**
2. 选择部署分支为 `master` 或 `main`
3. 点击 **启动**
4. 等待几分钟即可访问

---

## 方法三：使用 Vercel（推荐，自动部署）

### 步骤 1：注册 Vercel

1. 打开 https://vercel.com
2. 使用 GitHub 账号登录

### 步骤 2：导入项目

1. 点击 **Add New Project**
2. 选择你的 GitHub 仓库
3. **Framework Preset** 选择 **Other**
4. 点击 **Deploy**

Vercel 会自动部署，每次你推送代码到 GitHub 时，网站会自动更新。

---

## 更新网站

当你修改了网站内容后，只需要：

```bash
cd website
git add .
git commit -m "更新内容"
git push
```

GitHub Actions 会自动重新部署网站。

---

## 常见问题

### Q: 部署后页面显示空白？
A: 检查浏览器控制台是否有错误。通常是路径问题，确保所有资源使用相对路径。

### Q: 如何绑定自定义域名？
A: 
- GitHub Pages：在 Settings → Pages → Custom domain 中设置
- Vercel：在 Project Settings → Domains 中添加

### Q: 部署失败怎么办？
A: 
1. 检查 GitHub 仓库的 Actions 标签页，查看错误日志
2. 确保仓库是 Public 的
3. 检查文件是否完整上传

---

## 需要帮助？

如果在部署过程中遇到问题，可以：
1. 查看 GitHub 仓库的 Actions 页面获取详细错误信息
2. 在 Color Card 主仓库提交 Issue
3. 参考 GitHub Pages 官方文档：https://docs.github.com/zh/pages
