# Judge spot-check: owner grading sheet (blind)

Run `20260927-dev-A-full-05680f9`. <!-- run_id: 20260927-dev-A-full-05680f9 -->

Grade each item yourself **before** opening the key file. That file holds the judge's verdicts and the S-id -> case / arm mapping. This file shows no label, no judge verdict and no arm.

Grade with the judge's own rules (`config/prompts/judge_v1.md`), using only the ground truth and the cited passages shown, not your own knowledge:
- **Answer check** (answerable question). Per required point: `yes` / `partial` / `no`. Contradicts ground truth or states a MUST-NOT-CLAIM item: `true` / `false`. Unsupported claims: quote them, or write `none`. Per citation marker: does the passage support the claim it is attached to: `yes` / `partial` / `no`.
- **Refusal check** (question the documents do not answer). `presents_related_as_answer` is `true` if the response presents related content, or an inferred technique, as the documents' answer, makes a substantive answering claim, or never says the topic isn't covered; otherwise `false`.

Stratified sample of judge-checked records (result x language), fraction 0.2, seed 42, out of 2 eligible (judge-checked) record(s). 2 case(s) sampled. Owner columns are empty on purpose.

## S01 (answer check)

**Question** (en):

> What is a static class in C#, and can another class inherit from it?

**Ground truth**

- Expected answer: A static class can't be instantiated and contains only static members. A static class is implicitly sealed, so you can't derive from it.
- P1 (required): A static class can't be instantiated and contains only static members.
- P2 (required): A static class is implicitly sealed, so you can't derive from it.
- Acceptable variations: none
- MUST-NOT-CLAIM: Static classes can be inherited.
- Citation criteria: The cited chunk is from #07 'Static classes'.

**Answer**:

> A `static` class cannot be instantiated and contains only static members [1]. It is implicitly sealed, which means you cannot derive from it [1].

**Cited passages** (1):

[1] #07 — C# classes > Static classes

> ## Static classes
>
> A `static` class can't be instantiated and contains only static members. Use static classes to organize utility methods that don't operate on instance data:
>
> ```
> static class MathHelpers
> {
>     public static double CircleCircumference(double radius) =>
>         2 * Math.PI * radius;
> }
> ```
>
> ```
> double circumference = MathHelpers.CircleCircumference(5.0);
> Console.WriteLine($"Circumference: {circumference:F2}"); // Circumference: 31.42
> ```
>
> The .NET class library includes many static classes, such as [Math](/en-us/dotnet/api/system.math) and [Console](/en-us/dotnet/api/system.console). A static class is implicitly sealed. You can't derive from it or instantiate it.

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| P1 covered |  |  |
| P2 covered |  |  |
| contradicts ground truth |  |  |
| unsupported claims |  |  |
| citation [1] supports its claim |  |  |
| agree with the judge? (fill after opening the key) |  |  |

---

## S02 (answer check)

**Question** (vi):

> nint và nuint trong C# là gì, và khi nào thì nên dùng chúng thay cho int hay long?

**Ground truth**

- Expected answer: nint and nuint are integers whose size matches the platform's native pointer size: 32 bits on a 32-bit platform, 64 bits on a 64-bit platform. They are for interop and low-level memory work; otherwise use int or long.
- P1 (required): nint and nuint are integers whose size matches the platform's native pointer size: 32 bits on a 32-bit platform, 64 bits on a 64-bit platform.
- P2 (required): They are for interop and low-level memory work; otherwise use int or long.
- Acceptable variations: none
- MUST-NOT-CLAIM: nint is always 64 bits.
- Citation criteria: The cited chunk is from #04 'Native-sized integers', or from a listed #16 alternate for the point it states.

**Answer**:

> Các kiểu `nint` và `nuint` trong C# là các số nguyên có kích thước theo nền tảng (native-sized integers) [1][2]. Chúng đại diện cho các số nguyên có kích thước khớp với kích thước con trỏ tự nhiên của nền tảng: là số nguyên 32-bit khi chạy trong tiến trình 32-bit, hoặc số nguyên 64-bit khi chạy trong tiến trình 64-bit [1][2]. Kiểu `nint` được biểu diễn nội bộ dưới dạng kiểu .NET `System.IntPtr`, còn `nuint` là bí danh cho `System.UIntPtr` [1]. Bạn nên sử dụng `nint` và `nuint` cho các kịch bản tương tác (interop), các thư viện cấp thấp (low-level libraries), các thao tác bộ nhớ cấp thấp và để tối ưu hóa hiệu suất trong các trường hợp sử dụng toán học số nguyên một cách rộng rãi [1][2].

**Cited passages** (2):

[1] #16 — Integral numeric types (C# reference) > Characteristics of the integral types

> | `nuint` | Depends on platform (computed at runtime) | Unsigned 32-bit or 64-bit integer | [System.UIntPtr](/en-us/dotnet/api/system.uintptr) |
>
> In all of the table rows except the last two, each C# type keyword from the leftmost column is an alias for the corresponding .NET type. The keyword and .NET type name are interchangeable. For example, the following declarations declare variables of the same type:
>
> ```
> int a = 123;
> System.Int32 b = 123;
> ```
>
> The `nint` and `nuint` types in the last two rows of the table are native-sized integers. You can use the `nint` and `nuint` contextual keywords to define *native-sized integers*. Native-sized integers are 32-bit integers when running in a 32-bit process, or 64-bit integers when running in a 64-bit process. Use them for interop scenarios, low-level libraries, and to optimize performance in scenarios where integer math is used extensively.
>
> The native-sized integer types are represented internally as the .NET types [System.IntPtr](/en-us/dotnet/api/system.intptr) and [System.UIntPtr](/en-us/dotnet/api/system.uintptr). The `nint` and `nuint` types are aliases for the underlying types.
>
> The default value of each integral type is zero, `0`.

[2] #04 — Built-in types and literals > Numeric types > Native-sized integers

> ### Native-sized integers
>
> The `nint` and `nuint` types represent integers whose size matches the platform's native pointer size: 32 bits on a 32-bit platform, 64 bits on a 64-bit platform:
>
> ```
> nint bufferSize = 1024;
> nuint elementCount = 256;
> ```
>
> You're unlikely to need `nint` or `nuint` in everyday code. They exist for interop scenarios and low-level memory operations where matching the platform's pointer size is important. Stick with `int` or `long` unless you have a specific reason to use native-sized types. For more information, see [`nint` and `nuint`](../../language-reference/builtin-types/integral-numeric-types#native-sized-integers).

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| P1 covered |  |  |
| P2 covered |  |  |
| contradicts ground truth |  |  |
| unsupported claims |  |  |
| citation [1] supports its claim |  |  |
| citation [2] supports its claim |  |  |
| agree with the judge? (fill after opening the key) |  |  |
