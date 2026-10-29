# Rà soát toàn bộ source MAT CLI

Ngày: 2026-10-29. Bản fork được đọc: `71b5d3dced0183e52d85d7ff97cc7ec16db737d6`.
Bản upstream đối chiếu: `appian/cli-mat-plugin@28de18537cf6aa19c289adaa3bc6e9a0dd03ccc1`.

## Kết luận

Không tìm thấy backdoor hoặc mã cố ý đánh cắp dữ liệu trong source đã đọc.
Không thấy CLI tự mở listener mạng, gửi heap/credential ra server, tải payload
ở runtime, gọi shell ẩn, cài persistence, hoặc có nhánh mật khẩu bí mật.
Kết luận này áp dụng cho source tại hai commit trên, không chứng nhận mọi
phiên bản, toàn bộ lịch sử Git hoặc mọi binary/dependency là sạch tuyệt đối.

Đây là lần đọc nội dung và lần theo luồng gọi, không chỉ tìm từ khóa. Đã đọc
các điểm vào ứng dụng, mọi command/state/list manager, phân tích suspects,
known-object/resolver, helper, test, ví dụ extension, script và cấu hình build.
Sau đó đối chiếu phần khác nhau với upstream, kể cả các hook đã bị loại bỏ.
Tìm từ khóa và kiểm tra ký tự điều khiển Unicode được dùng bổ trợ; không thấy
ký tự định dạng Unicode ẩn trong 133 file được theo dõi ở commit fork này.

## Phạm vi đọc

| Nhóm | Số file | Phạm vi |
| --- | ---: | --- |
| Java runtime CLI | 85 | Toàn bộ nội dung, gồm giao diện JSON mới |
| Java unit test | 10 | Toàn bộ nội dung, không đóng gói vào runtime |
| Java example extension | 3 | Toàn bộ nội dung; module đang tắt |
| Java tạo heap giả lập | 1 | Chỉ tạo dữ liệu synthetic để test |
| Python và shell launcher | 3 | Download, giải nén, gọi JVM, đóng gói, test |
| Maven POM | 6 | Dependency, plugin, phase và profile |
| XML khác, manifest, properties, schema | 10 | Entrypoint, extension và nội dung đóng gói |
| GitHub Actions | 1 | Download toolchain, build/test, upload artifact |
| Fixture, lock, ignore, tài liệu, giấy phép | 14 | Cấu hình/dữ liệu và ngữ cảnh |
| Tổng | 133 | Không gồm file sinh ra hoặc binary dependency |

Danh sách file và SHA-256 ở [SOURCE_REVIEW_FILES.tsv](SOURCE_REVIEW_FILES.tsv)
xác định chính xác snapshot được rà soát. Bản upstream có 124 file theo dõi;
các file dùng chung được đối chiếu byte, phần thay đổi và file chỉ có ở upstream
được đọc riêng. Không chạy script upstream trong lần rà soát này.

## Các hành vi dễ bị hiểu nhầm

- `Executor` và `CommandExecutor` là lớp điều phối phân tích snapshot, không phải
  lớp chạy lệnh hệ điều hành. Các thao tác `resolveValue`, references và OQL
  truy cập mô hình heap do MAT cung cấp.
- `java.net.URI`, `java.lang.Runtime` và `sun.management.RuntimeImpl` xuất hiện
  dưới dạng tên lớp cần tìm trong heap. Các chỗ đó không mở mạng hay chạy process.
- [Extension resolver](../CliMatPlugin/src/main/java/com/appiansupport/mat/resolvers/IEclipsePluginExtensionResolver.java)
  gọi `createExecutableExtension`: chạy Java của plugin đã được cài vào Eclipse.
  Đây là cơ chế mở rộng công khai, không phải sandbox. Cần tin cậy plugin đã cài.
- [Hướng dẫn upstream](UPSTREAM.md) có ví dụ bật JDWP cổng 5005 để debug.
  Đây là hướng dẫn bật thủ công. Launcher, CI và cấu hình MAT đã kiểm tra không
  tự thêm `-agentlib:jdwp` hay `-javaagent`.
- [Bundler](../scripts/bundle.py) tải MAT/JRE từ URL cố định trong lock, kiểm tra
  hash trước giải nén rồi gọi p2 director bằng danh sách argument, không dùng
  `shell=True` hoặc tải script từ mạng rồi thực thi. Build Maven vẫn tin cậy
  các build plugin/dependency được tải về.
- [Launcher](../scripts/mat-cli) gọi JVM đi kèm, quote các đường dẫn/argument và
  giới hạn cú pháp biến heap size. Các biến môi trường JVM chuẩn vẫn là một phần
  môi trường thực thi; launcher không phải ranh giới sandbox chống môi trường độc hại.
- Upstream có script cleanup dùng `rm -rf $(find ...)` và `xargs rm` thiếu xử lý
  tên file an toàn, cùng hook tự install/uninstall plugin trong phase package.
  Những phần đó đã bị bỏ trước v0.1.0. Chúng là hành vi build được khai báo;
  bản thân chúng không chứng minh upstream có backdoor.

## Vấn đề thực tế còn tồn tại

Các điểm dưới đây được suy ra trực tiếp từ code. Chưa viết PoC tấn công hoặc
bổ sung test cho chúng trong lần đọc này. Theo yêu cầu chỉ đọc kỹ, lần này
không thay đổi runtime hay xuất bản binary mới.

### 1. Báo cáo legacy có thể ghi đè hoặc theo symlink

[Executor](../CliMatPlugin/src/main/java/com/appiansupport/mat/Executor.java)
dòng 98–100 đặt tên báo cáo theo thời gian đến giây; dòng 141 mở bằng
`FileOutputStream(path, false)`. Không có tạo-file-mới độc quyền, chống symlink
hoặc đặt quyền owner-only.

Hai lần chạy trùng tên có thể ghi đè kết quả. Trong thư mục heap do bên khác
cũng ghi được, symlink có tên khớp có thể chuyển đích ghi sang file mà tiến trình
có quyền ghi. Với umask thông thường 022, file báo cáo mới cũng có thể đọc được
bởi user khác. Báo cáo chứa chuỗi và thông tin nhạy cảm từ heap.

Đề xuất: tạo tên duy nhất bằng API tạo file mới, đặt quyền riêng tư khi tạo,
không theo symlink, kiểm tra lỗi ghi và không báo thành công khi ghi thất bại.
Cần thư mục heap riêng tư cả với các index/sidecar do MAT quản lý.

### 2. Nhánh lỗi trong tìm common parent có thể lặp mãi

[SuspectClassBuilder](../CliMatPlugin/src/main/java/com/appiansupport/mat/suspects/SuspectClassBuilder.java)
dòng 126–149: nếu `snapshot.getObject(parentRecord.getObjectId())` liên tục
ném `SnapshotException`, catch chỉ ghi lỗi. `parentRecord` không tiến lên,
không break và không kiểm tra cancellation trong vòng lặp đó.

Hệ quả có thể là CPU/log tăng liên tục khi snapshot rơi vào trạng thái lỗi.
Đây là lỗi độ bền, không phải bằng chứng có mã chủ ý gây hại. Đề xuất thoát
nhánh lỗi và kiểm tra cancellation/giới hạn bước.

### 3. Output legacy không lọc escape sequence từ heap

[ObjectUtils](../CliMatPlugin/src/main/java/com/appiansupport/mat/utils/ObjectUtils.java)
in chuỗi lấy từ heap; [CommandExecutor](../CliMatPlugin/src/main/java/com/appiansupport/mat/console/CommandExecutor.java)
in primitive array, tên và kết quả truy vấn thẳng ra terminal.

Chuỗi chứa ký tự điều khiển có thể làm sai lệch hiển thị terminal. Với heap
không tin cậy, nên escape ký tự điều khiển trước khi hiển thị. Bộ mã hóa JSON
mới có escape ký tự ASCII control, nhưng điều đó không bảo vệ mọi output
legacy hoặc log/progress của MAT.

### 4. Một số lỗi chức năng legacy/example chưa được test bao phủ

- [CommandExecutor](../CliMatPlugin/src/main/java/com/appiansupport/mat/console/CommandExecutor.java)
  dòng 453–455 luôn đọc 1000 phần tử dominator, kể cả khi mảng ngắn hơn.
  Có thể ném lỗi vượt chỉ số; controller hiện có thể hiểu nhầm là lỗi chọn menu.
- [ListManager](../CliMatPlugin/src/main/java/com/appiansupport/mat/console/listmanager/ListManager.java)
  biên dịch regex do người dùng nhập mà không bắt `PatternSyntaxException`.
  Regex không hợp lệ có thể làm CLI legacy kết thúc; regex tốn thời gian không
  có timeout riêng.
- [ReferenceIteratingKnownObject](../CliMatPlugin/src/main/java/com/appiansupport/mat/knownobjects/ReferenceIteratingKnownObject.java)
  có thể gọi `referencedThreads.isEmpty()` trước khi trường này được khởi tạo.
- [Module ví dụ](../ExampleExtensionPlugin/) có constructor sai số argument,
  thiếu import/tên biến, tên public class/package không khớp file/plugin.xml
  và version parent không khớp reactor. Module bị tắt và không nằm trong bundle;
  không nên quảng bá nó là ví dụ chỉ cần bật là build được.
- Pagination ở giao diện JSON giới hạn số hàng xuất, không giới hạn chi phí
  phân tích/query, độ dài mỗi ô hay số byte của text fallback.

## Giới hạn của việc đọc source

Mã MAT, Equinox, Apache Commons, JRE và Maven build plugin vẫn nằm ngoài phạm vi
đọc toàn bộ này. Không suy diễn checksum đúng thành “không có malware”. Không
suy diễn 92 unit test và 27 integration check đã qua thành các nhánh lỗi trên
đã được kiểm thử. Kết quả test trước đó ở [VALIDATION.md](VALIDATION.md).

Kết luận phù hợp: **không tìm thấy backdoor trong source repo đã đọc; có các
điểm cần gia cố đã ghi rõ ở trên**. Chưa có căn cứ để gắn nhãn upstream có virus
hoặc cam kết toàn bộ bundle sạch 100%.
