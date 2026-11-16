# CESNET XS census 哈希更正：生成字节与 Git 检出字节

2026-11-10 census 的 CSV 由 Python `csv` 写出 CRLF，原 JSON 和协议记录的是**生成文件的原始字节哈希**。仓库 `.gitattributes` 对 CSV 使用 LF，提交后 Git blob 与检出文件使用 LF，所以历史原始哈希不能直接用于核验仓库检出文件。2026-11-12 对四个文件逐字节核验：将本地生成文件的 CRLF 替换为 LF 后，与当前 Git blob 完全一致；行和统计没有改变。旧哈希保留以标识当时的生成文件。

| 文件 | 原始生成文件 SHA-256 | Git blob / LF 规范化 SHA-256 |
|---|---|---|
| DAILY_CENSUS | `53c2eb70fb7efd23d43d0aabfaaab4a79c2b13c3459941a329ac8cca6af90d84` | `e546a89b85338ef764c78ab09bab77cfc124f97afe6cecea4cb0dd16d19416b1` |
| DATE_APP_COUNTS | `90a91706bf8f32c5948127adc052c6043385523f86d481e338ef6809f18cac69` | `bd5331a573168e593ed6a5608212cbd409baa359af213c5cc4ed6ae8006493c9` |
| WEEKLY_CENSUS | `dc37522c8766aa16667a1941d949fb916cf837352f69cf18198d0bf064d53c9a` | `026fc91301926869c3f0cf29715104aa103e481c8aa261560e18bc8b0cd478dc` |
| SPLIT_MANIFEST | `00b4baed8fe2543e568094e92596cb8a37b4a7bc6d62708779efcf036b99cc7a` | `9eb553e31354665e5d15b5b4b0f4f1f13bac0b252562c9350f772d0e0aa4f33d` |

W15 控制脚本在核验输入前将 CRLF 转换为 LF，再检查后两项的固定 SHA-256；HDF5 原始归档依旧按未变换字节核验。哈希只验证文件一致性，不证明历史实验独立真实性。
