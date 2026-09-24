# Integral numeric types (C# reference) - Microsoft Learn

Source: https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/builtin-types/integral-numeric-types

---

---

Note

Access to this page requires authorization. You can try [signing in](#) or changing directories.

Access to this page requires authorization. You can try changing directories.

# Integral numeric types (C# reference)

The *integral numeric types* represent integer numbers. All integral numeric types are [value types](value-types). The integral types are [simple types](value-types#built-in-value-types) and you initialize them with [literals](#integer-literals). All integral numeric types support [arithmetic](../operators/arithmetic-operators), [bitwise logical](../operators/bitwise-and-shift-operators), [comparison](../operators/comparison-operators), and [equality](../operators/equality-operators) operators.

The C# language reference documents the most recently released version of the C# language. It also contains initial documentation for features in public previews for the upcoming language release.

The documentation identifies any feature first introduced in the last three versions of the language or in current public previews.

Tip

To find when a feature was first introduced in C#, consult the article on the [C# language version history](../../whats-new/csharp-version-history).

## Characteristics of the integral types

C# supports the following predefined integral types:

| C# type/keyword | Range | Size | .NET type |
| --- | --- | --- | --- |
| `sbyte` | -128 to 127 | Signed 8-bit integer | [System.SByte](/en-us/dotnet/api/system.sbyte) |
| `byte` | 0 to 255 | Unsigned 8-bit integer | [System.Byte](/en-us/dotnet/api/system.byte) |
| `short` | -32,768 to 32,767 | Signed 16-bit integer | [System.Int16](/en-us/dotnet/api/system.int16) |
| `ushort` | 0 to 65,535 | Unsigned 16-bit integer | [System.UInt16](/en-us/dotnet/api/system.uint16) |
| `int` | -2,147,483,648 to 2,147,483,647 | Signed 32-bit integer | [System.Int32](/en-us/dotnet/api/system.int32) |
| `uint` | 0 to 4,294,967,295 | Unsigned 32-bit integer | [System.UInt32](/en-us/dotnet/api/system.uint32) |
| `long` | -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807 | Signed 64-bit integer | [System.Int64](/en-us/dotnet/api/system.int64) |
| `ulong` | 0 to 18,446,744,073,709,551,615 | Unsigned 64-bit integer | [System.UInt64](/en-us/dotnet/api/system.uint64) |
| `nint` | Depends on platform (computed at runtime) | Signed 32-bit or 64-bit integer | [System.IntPtr](/en-us/dotnet/api/system.intptr) |
| `nuint` | Depends on platform (computed at runtime) | Unsigned 32-bit or 64-bit integer | [System.UIntPtr](/en-us/dotnet/api/system.uintptr) |

In all of the table rows except the last two, each C# type keyword from the leftmost column is an alias for the corresponding .NET type. The keyword and .NET type name are interchangeable. For example, the following declarations declare variables of the same type:

```
int a = 123;
System.Int32 b = 123;
```

The `nint` and `nuint` types in the last two rows of the table are native-sized integers. You can use the `nint` and `nuint` contextual keywords to define *native-sized integers*. Native-sized integers are 32-bit integers when running in a 32-bit process, or 64-bit integers when running in a 64-bit process. Use them for interop scenarios, low-level libraries, and to optimize performance in scenarios where integer math is used extensively.

The native-sized integer types are represented internally as the .NET types [System.IntPtr](/en-us/dotnet/api/system.intptr) and [System.UIntPtr](/en-us/dotnet/api/system.uintptr). The `nint` and `nuint` types are aliases for the underlying types.

The default value of each integral type is zero, `0`.

Each of the integral types has `MinValue` and `MaxValue` properties that provide the minimum and maximum value of that type. These properties are compile-time constants except for the case of the native-sized types (`nint` and `nuint`). The `MinValue` and `MaxValue` properties are calculated at runtime for native-sized types. The sizes of those types depend on the process settings.

Use the [System.Numerics.BigInteger](/en-us/dotnet/api/system.numerics.biginteger) structure to represent a signed integer with no upper or lower bounds.

## Integer literals

Integer literals can be:

- *decimal*: without any prefix
- *hexadecimal*: with the `0x` or `0X` prefix
- *binary*: with the `0b` or `0B` prefix

The following code demonstrates an example of each:

```
var decimalLiteral = 42;
var hexLiteral = 0x2A;
var binaryLiteral = 0b_0010_1010;
```

The preceding example also shows the use of `_` as a *digit separator*. You can use the digit separator with all kinds of numeric literals.

The suffix determines the type of an integer literal as follows:

- If the literal has no suffix, the compiler assigns the type as the first of the following types in which its value can be represented: `int`, `uint`, `long`, `ulong`.

  Note

  The compiler interprets literals as positive values. For example, the literal `0xFF_FF_FF_FF` represents the number `4,294,967,295` of the `uint` type, though it has the same bit representation as the number `-1` of the `int` type. If you need a value of a certain type, cast a literal to that type. Use the `unchecked` operator if a literal value can't be represented in the target type. For example, `unchecked((int)0xFF_FF_FF_FF)` produces `-1`.
- If the literal includes the `U` or `u` suffix, the compiler assigns the type as the first of the following types in which its value can be represented: `uint`, `ulong`.
- If the literal includes the `L` or `l` suffix, the compiler assigns the type as the first of the following types in which its value can be represented: `long`, `ulong`.

  Note

  You can use the lowercase letter `l` as a suffix. However, `l` generates a compiler warning because the letter `l` can be confused with the digit `1`. Use `L` for clarity.
- If the literal includes one of the `UL`, `Ul`, `uL`, `ul`, `LU`, `Lu`, `lU`, or `lu` suffixes, the compiler assigns the type as `ulong`.

If the value represented by an integer literal exceeds [UInt64.MaxValue](/en-us/dotnet/api/system.uint64.maxvalue#system-uint64-maxvalue), a compiler error [CS1021](../compiler-messages/overloaded-operator-errors#overflow-and-underflow-errors) occurs.

If the compiler determines the type of an integer literal as `int` and the value represented by the literal is within the range of the destination type, the value can be implicitly converted to `sbyte`, `byte`, `short`, `ushort`, `uint`, `ulong`, `nint`, or `nuint`:

```
byte a = 17;
byte b = 300;   // CS0031: Constant value '300' cannot be converted to a 'byte'
```

As the preceding example shows, if the literal's value isn't within the range of the destination type, a compiler error [CS0031](../compiler-messages/overloaded-operator-errors#overflow-and-underflow-errors) occurs.

You can also use a cast to convert the value represented by an integer literal to the type other than the determined type of the literal:

```
var signedByte = (sbyte)42;
var longVariable = (long)42;
```

## Conversions

You can convert any integral numeric type to any other integral numeric type. If the destination type can store all values of the source type, the conversion is implicit. Otherwise, use a [cast expression](../operators/type-testing-and-cast#cast-expression) to perform an explicit conversion. For more information, see [Built-in numeric conversions](numeric-conversions).

## Native sized integers

Native sized integer types have special behavior because the storage matches the natural integer size on the target machine.

- To get the size of a native-sized integer at run time, use `sizeof()`. However, the code must be compiled in an unsafe context. For example:

  ```
  Console.WriteLine($"size of nint = {sizeof(nint)}");
  Console.WriteLine($"size of nuint = {sizeof(nuint)}");

  // output when run in a 64-bit process
  //size of nint = 8
  //size of nuint = 8

  // output when run in a 32-bit process
  //size of nint = 4
  //size of nuint = 4
  ```

  You can also get the equivalent value from the static [IntPtr.Size](/en-us/dotnet/api/system.intptr.size#system-intptr-size) and [UIntPtr.Size](/en-us/dotnet/api/system.uintptr.size#system-uintptr-size) properties.
- To get the minimum and maximum values of native-sized integers at run time, use `MinValue` and `MaxValue` as static properties with the `nint` and `nuint` keywords, as in the following example:

  ```
  Console.WriteLine($"nint.MinValue = {nint.MinValue}");
  Console.WriteLine($"nint.MaxValue = {nint.MaxValue}");
  Console.WriteLine($"nuint.MinValue = {nuint.MinValue}");
  Console.WriteLine($"nuint.MaxValue = {nuint.MaxValue}");

  // output when run in a 64-bit process
  //nint.MinValue = -9223372036854775808
  //nint.MaxValue = 9223372036854775807
  //nuint.MinValue = 0
  //nuint.MaxValue = 18446744073709551615

  // output when run in a 32-bit process
  //nint.MinValue = -2147483648
  //nint.MaxValue = 2147483647
  //nuint.MinValue = 0
  //nuint.MaxValue = 4294967295
  ```
- While the full range of `nint` and `nuint` can be larger, compile-time constants are restricted to a 32-bit range:

  - For `nint`: [Int32.MinValue](/en-us/dotnet/api/system.int32.minvalue#system-int32-minvalue) to [Int32.MaxValue](/en-us/dotnet/api/system.int32.maxvalue#system-int32-maxvalue).
  - For `nuint`: [UInt32.MinValue](/en-us/dotnet/api/system.uint32.minvalue#system-uint32-minvalue) to [UInt32.MaxValue](/en-us/dotnet/api/system.uint32.maxvalue#system-uint32-maxvalue).
- The compiler provides implicit and explicit conversions to other numeric types. For more information, see [Built-in numeric conversions](numeric-conversions).
- There's no direct syntax for native-sized integer literals. There's no suffix to indicate that a literal is a native-sized integer, such as `L` to indicate a `long`. Use implicit or explicit casts of other integer values instead. For example:

  ```
  nint a = 42
  nint a = (nint)42;
  ```

## C# language specification

For more information, see the following sections of the [C# language specification](../language-specification/readme):

- [Integral types](../language-specification/types#836-integral-types)
- [Integer literals](../language-specification/lexical-structure#6453-integer-literals)
- [Native sized integral types](../language-specification/types#836-integral-types)

## See also

- [Value types](value-types)
- [Floating-point types](floating-point-numeric-types)
- [Standard numeric format strings](../../../standard/base-types/standard-numeric-format-strings)
- [Numerics in .NET](../../../standard/numerics)

---

## Additional resources

---

- Last updated on 
  2026-01-20
