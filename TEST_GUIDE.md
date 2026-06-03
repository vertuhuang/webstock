# 股票实时监控系统 - 本地测试指南

## 📍 项目位置
```
/Users/vertu.huang/Desktop/webstock/
```

## 🚀 测试步骤

### 步骤1：启动后端服务器

**打开终端，执行：**
```bash
cd /Users/vertu.huang/Desktop/webstock
node server.js
```

**预期输出：**
```
Server started on port 3000
```

**如果报错：**
- 检查`node_modules`是否安装：执行`npm install`
- 检查`server.js`语法：执行`node --check server.js`

---

### 步骤2：测试后端API（重要！）

**打开另一个终端，测试API是否工作：**

**测试1：健康检查**
```bash
curl <SIGNED_URL_REMOVED>
```
预期返回：`{"status":"ok"}`

**测试2：股票查询API**
```bash
curl -X POST <SIGNED_URL_REMOVED> \
  -H "Content-Type: application/json" \
  -d '{"codes":["sh600519","sz000001"]}'
```

**预期返回类似：**
```json
{
  "success": true,
  "data": [
    {
      "code": "sh600519",
      "name": "贵州茅台",
      "currentPrice": 1850.00,
      "change": 10.50,
      "changePercent": 0.57,
      "volume": 1234567,
      "turnoverRate": 0.12
    }
  ]
}
```

**如果API测试失败：**
- 检查服务器是否运行：`lsof -i :3000`
- 查看服务器日志：`cat server.log`（如果用了输出重定向）
- 把错误信息发给我

---

### 步骤3：打开前端页面

**在浏览器中访问：**
```
<SIGNED_URL_REMOVED>
```

**预期看到：**
- 仿Word文档样式的页面
- 标题"实时股票监控"
- 一个表格，包含"贵州茅台"和"格力电器"的初始数据
- 表格数据每3秒自动更新

---

### 步骤4：打开开发者工具，查看错误

**按F12（或右键->检查）打开开发者工具**

**切换到"Console"标签页，查看是否有红色错误：**

**常见错误及解决方法：**

#### 错误1：`Failed to fetch` 或 `Network Error`
**原因：** 后端服务器没有启动，或端口不对
**解决：** 确保后端服务器正在运行（步骤1）

---

#### 错误2：`HTTP error! status: 404`
**原因：** 前端调用的API路径不对
**解决：** 检查前端代码第359行，确保URL是`http://localhost:3000/api/stocks`

---

#### 错误3：`HTTP error! status: 500`
**原因：** 后端服务器内部错误
**解决：** 
1. 查看后端服务器终端的错误日志
2. 把错误日志发给我

---

#### 错误4：表格显示"-"或数据不更新
**原因：** 后端API返回的数据格式不对，或解析失败
**解决：**
1. 在Console标签页，找到`updateStockData`函数的`console.log`输出
2. 查看`result`对象的结构
3. 把Console截图或日志发给我

---

#### 错误5：`stock.name is undefined` 或类似错误
**原因：** 后端返回的股票对象缺少前端期望的字段
**解决：** 把完整的错误信息发给我

---

### 步骤5：测试添加/删除股票

**添加股票：**
1. 在页面底部的输入框输入股票代码（如`sh600519`）
2. 点击"添加"按钮
3. 表格应该新增一行

**删除股票：**
1. 点击某行末尾的"删除"按钮
2. 该行应该被删除

**如果添加/删除失败：**
- 检查浏览器Console是否有错误
- 把错误发给我

---

## 🔍 调试技巧

### 1. 查看前端Console日志
- 按F12 -> Console标签页
- 所有`console.log`和`console.error`都会显示在这里

### 2. 查看网络请求
- 按F12 -> Network标签页
- 刷新页面，查看`stocks` API请求
- 点击请求，查看Request和Response详情

### 3. 查看后端服务器日志
- 后端服务器运行的终端会显示所有`console.log`输出
- 如果服务器报错了，错误信息会显示在这里

### 4. 手动测试后端API
```bash
# 测试单个股票
curl -X POST <SIGNED_URL_REMOVED> \
  -H "Content-Type: application/json" \
  -d '{"codes":["sh600519"]}'

# 测试多个股票
curl -X POST <SIGNED_URL_REMOVED> \
  -H "Content-Type: application/json" \
  -d '{"codes":["sh600519","sz000001","hkhk00700"]}'
```

---

## 📧 遇到问题怎么办？

**把以下信息发给我：**
1. **错误截图**（浏览器Console或后端终端）
2. **完整的错误信息**（复制文本，不要只发截图）
3. **你已经尝试了什么**（比如"我重启了服务器，但还是报错"）

**我会帮你分析和修复！**

---

## ✅ 测试完成标准

当你完成以下所有操作时，测试通过：
- [ ] 后端服务器成功启动
- [ ] `curl <SIGNED_URL_REMOVED> 返回`{"status":"ok"}`
- [ ] 浏览器打开`<SIGNED_URL_REMOVED> 看到仿Word页面
- [ ] 页面表格显示股票数据，且每3秒自动更新
- [ ] 可以添加新股票
- [ ] 可以删除现有股票
- [ ] 浏览器Console没有红色错误

**如果以上任何一项失败，把错误发给我！**

---

## 🎉 测试通过后

测试通过后，你可以：
1. **自定义监控股票**：在页面底部添加你想监控的股票
2. **调整更新频率**：修改`stock-monitor.html`第445行的`3000`（毫秒）
3. **部署到生产环境**：如果需要，我可以帮你部署到云服务器

---

**现在开始测试吧！遇到问题随时找我。**
