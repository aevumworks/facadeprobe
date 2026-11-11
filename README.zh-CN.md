# FacadeProbe

一套可编辑的建筑立面视觉测试场景，用来检查门窗可见标签、相机投影和遮挡。

**1 栋原创建筑，3 种配对状态，4 个固定相机，共 12 个真实渲染视图。** 包含 `.blend`、`.glb`、RGB、语义/实例遮罩、相机 Z 深度、OpenCV 相机矩阵及可见实例标注。双击 HTML 即可查看实际数据。

[English](README.md) · [下载 v0.1.0](https://github.com/aevumworks/facadeprobe/releases/tag/v0.1.0)

![真实资源查看器](https://github.com/aevumworks/facadeprobe/releases/download/v0.1.0/preview.png)

这是用于建筑 CV 调试的小型合成资源。一栋建筑不能代表真实建筑分布，也不是训练基准、工程 BIM 或识别精度证明。

## 下载后怎么用

1. 下载并解压 `facadeprobe-0.1.0-resource.zip`。
2. 双击 `data/index.html`，无需安装和启动服务器。
3. 切换无遮挡、阳台遮挡、前景格栅，以及正面、左/右斜视和高机位；比较 RGB、语义、叠加或深度。
4. 选择门窗实例，读取真实可见像素数和边界框，显示可见实例框。右侧可取得该状态的源场景、通用模型和对应相机/标注 JSON。
5. 使用 Blender **5.2** 打开 `.blend` 编辑；`.glb` 可导入兼容工具。计算机视觉投影使用相机 JSON，不根据网页显示尺寸猜相机内参。

正面视角中，窗户 101 从无遮挡的 **9,925 像素**变为前景遮挡后的 **499 像素**，可见面积相对减少约 **94.972%**。这是几何可见像素变化，不是模型检测结果；建筑里的实例并未因此消失。

## 数据定义

- 图像为 960×720，真实 Cycles CPU 渲染，12 samples 加去噪。遮罩来自同一相机、同一几何的 Object Index 通道，不是对 RGB 做模型预测。
- `semantic.png` 为 uint8 类别 ID：0 背景，1 墙体/饰面，2 窗框/窗面，3 门，4 阳台/栏杆，5 格栅/挡板，6 地面，7 屋顶/女儿墙。
- `instance.png` 为 uint16 稳定实例 ID。读取时不要转成 8 位；可见边界框和面积在 `annotations.json`，不可见时面积 0、框为 null。
- `depth-z.npy` 为 float32 相机 Z，单位米，背景 NaN；它不是射线欧氏距离。`depth-preview.png` 仅显示固定 0—35m 色带，不能当数值深度。
- 世界坐标右手系，X 沿立面，Z 向上，正面朝 −Y。相机遵循 OpenCV：X 右、Y 下、Z 前；像素中心为 `(x+0.5,y+0.5)`，没有镜头畸变。
- 遮罩只标可见表面，不补画被挡住的完整窗户。窗框、窗面和中梃归为窗；窗台归墙/饰面。窗面采用不透明材质，不模拟物理玻璃透射。
- `.blend` 保存相对输出路径；`.glb` 为通用几何交换格式，不承诺与 Blender 像素完全相同。CV 的 K 和外参以 JSON 为准。

### GLB 在普通 glTF 引擎中的坐标

GLB 原生是 glTF 的 **Y-up**，相机 JSON/Blender 世界是 **Z-up**：dataset `[X,Y,Z]` → glTF `[X,Z,-Y]`；反向 `[x,y,z]` → dataset `[x,-z,y]`。齐次列向量变换为：

```text
M_gltf_from_dataset = [[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1]]
M_dataset_from_gltf = [[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]]
p_cv = world_to_camera_cv @ M_dataset_from_gltf @ p_gltf_world
```

例如正面相机在数据世界约 `[0,-20,5.6]`，在原生 GLB 世界是 `[0,5.6,20]`；注视点 `[0,0,4.4]` 转为 `[0,4.4,0]`，正确换系后都投到约 `[480,360]` 像素。原生 glTF 相机自身沿 −Z 看、+Y 向上；JSON/OpenCV 相机沿 +Z 看、+Y 向下，两者的局部轴转换为 `diag(1,-1,-1,1)`，与世界换系分开处理。不能把 JSON 外参直接套到 Y-up GLB 顶点。

完整推导见 [字段契约](docs/CONTRACT.md)。转换矩阵已写入 manifest；`gltf-coordinate-validation.json` 直接解析原生 GLB 节点进行校验，没有借助 Blender 导入自动换轴。

源场景、12 视图及原始 EXR 通道的完整目录见 [英文说明](README.md) 和 [字段契约](docs/CONTRACT.md)。

## 从源码复现

需要 Blender **5.2**，以及独立 Python 环境中的 NumPy、Pillow 和 OpenEXR。`requirements.txt` 给出依赖。当前实际环境是 Windows 11、Blender 5.2.0 LTS、Python 3.14.7、NumPy 2.5.4、Pillow 12.3.0、OpenEXR 3.5.3。

在项目根目录运行，`blender`、`python` 可替换为对应程序完整路径：

```sh
blender --background --factory-startup --python-exit-code 1 --python scripts/generate.py -- --output data
python scripts/process_validate.py data
blender --background --factory-startup --python-exit-code 1 --python scripts/verify_import.py -- data
python scripts/verify_gltf_coordinates.py data
python scripts/build_viewer.py data
```

生成目录不能已经存在，复现请换一个新目录。生成器在自己新开的后台进程中重置场景，不要把它粘进正在使用的 Blender 场景执行。没有连接现有 Blender UI，也不修改全局偏好。

生成器支持 `--width`、`--height`、`--samples`、`--threads`、`--cases`、`--views` 做小规模调试；正式资源与查看器对应默认 3×4 完整组合。修改配置或源模型后需重新验证，当前报告不替修改后的模型背书。

## 已完成的验证

12 个视图均通过标签 PNG 回读、尺寸、类别/实例映射、面积/边界框及独立几何光线核对：共 **4,894 个内部采样点，标签不一致 0 个**。已知三维点与 Blender 原生投影最大差约 **0.0000872 像素**；建筑表面相机 Z 深度最大差约 **0.0001851 米**。检查通过 5×5 同实例邻域排除边界，不能据此声称每个抗锯齿边缘完全无误差。

人为把主点移 12 像素、同时上下翻转标签和深度、把深度乘 1000，验证均拒绝。三个 `.blend` 均实际重开，三个 `.glb` 均在新场景重新导入，核对了网格数、语义/实例 ID、世界范围和相机姿态。查看器实际检查了切换、实例数据、框、文件链接、键盘与桌面/窄屏布局。

报告在资源包 `data/validation.json`、`data/import-validation.json`。[验证说明](docs/VALIDATION.md)

未在 macOS、Linux、第三方 GLB 软件或手机实机验收；未训练模型。可见性比较只在同一相机的配对状态间使用，不能把同一建筑视图拆成独立训练/测试样本。

## 来源与许可

代码、网格、材质、渲染和标注均由 Aevum 为本项目独立创建，采用 [MIT](LICENSE) 许可证。无客户图纸、私有业务源码、现成模型或第三方纹理。

[BlenderProc](https://github.com/DLR-RM/BlenderProc) 提供更完整的通用合成渲染流程；[Blender Facade Synthesis](https://github.com/LeoAKALiu/blender-facade-synthesis) 已描述立面训练数据生产流程。本项目取更小的可检查场景范围，没有复制它们的代码，也不声称存在市场空白。

Blender、NumPy、Pillow、OpenEXR 是外部依赖，各自许可不变；发行包不包含它们的程序或源码。[版本说明](CHANGELOG.md)
