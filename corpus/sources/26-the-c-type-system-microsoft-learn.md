# The C# type system - Microsoft Learn

Source: https://learn.microsoft.com/en-us/dotnet/csharp/fundamentals/types/

---

---

Note

Access to this page requires authorization. You can try [signing in](#) or changing directories.

Access to this page requires authorization. You can try changing directories.

# The C# type system

Tip

**New to developing software?** Start with the [Get started](../../tour-of-csharp/tutorials/) tutorials first. They walk you through writing programs and introduce types as you go.

**Experienced in another language?** If you already understand type systems, skim the [value vs. reference](#value-types-and-reference-types) distinction and the [choose which kind of type](#choose-which-kind-of-type) guide, then jump to the articles on specific types.

C# is a strongly typed language. Every variable, constant, and expression has a type. The compiler enforces *type safety* by checking that every operation in your code is valid for the types involved. For example, you can add two `int` values, but you can't add an `int` and a `bool`:

```
int a = 5;
int b = a + 2; // OK

bool test = true;

// Error. Operator '+' cannot be applied to operands of type 'int' and 'bool'.
// int c = a + test;
```

Note

Unlike C and C++, in C#, `bool` isn't convertible to `int`.

Type safety catches errors at compile time, before your code runs. The compiler also embeds type information into the executable as metadata, which the common language runtime (CLR) uses for additional safety checks at run time.

## Declare variables with types

When you declare a variable, you specify its type explicitly or use `var` to let the compiler infer the type from the assigned value:

```
// Explicit type:
int count = 10;
double temperature = 36.6;

// Compiler-inferred type:
var name = "C#";
var items = new List<string> { "one", "two", "three" };
```

Method parameters and return values also have types. The following method takes a `string` and an `int`, and returns a `string`:

```
static string GetGreeting(string name, int visitCount)
{
    return visitCount switch
    {
        1 => $"Welcome, {name}!",
        _ => $"Welcome back, {name}! Visit #{visitCount}."
    };
}
```

After you declare a variable, you can't change its type or assign a value that's incompatible with the declared type. You can convert values to other types. The compiler performs *implicit conversions* that don't lose data automatically. *Explicit conversions* (casts) require you to indicate the conversion in your code. For more information, see [Casting and type conversions](../../programming-guide/types/casting-and-type-conversions).

## Built-in types and custom types

C# provides [built-in types](built-in-types) for common data: integers, floating-point numbers, `bool`, `char`, and `string`. Every C# program can use these built-in types without any extra references.

Beyond built-in types, you can create your own types by using several constructs:

- [**Classes**](classes) — Reference types for modeling behavior and complex objects. Support inheritance and polymorphism.
- [**Structs**](structs) — Value types for small, lightweight data. Each variable holds its own copy.
- [**Records**](records) — Classes or structs with compiler-generated equality, `ToString`, and nondestructive mutation through `with` expressions.
- [**Interfaces**](interfaces) — Contracts that define members any class or struct can implement.
- [**Enumerations**](enums) — Named sets of integral constants, such as days of the week or file access modes.
- [**Tuples**](../../language-reference/builtin-types/value-tuples) — Lightweight structural types that group related values without defining a named type.
- [**Generics**](generics) — Type-parameterized constructs like `List<T>` and `Dictionary<TKey, TValue>` that provide type safety while reusing the same logic for different types.

## Value types and reference types

Every type in C# is either a *value type* or a *reference type*. This distinction determines how variables store data and how assignment works.

**Value types** hold their data directly. When you assign a value type to a new variable, the runtime copies the data. Changes to one variable don't affect the other. Structs, enums, and the built-in numeric types are all value types.

**Reference types** hold a reference to an object on the managed heap. When you assign a reference type to a new variable, both variables point to the same object. Changes through one variable are visible through the other. Classes, arrays, delegates, and strings are reference types.

The following example shows the difference. The first block shows the definition for the `Coords` record struct, which is a value type. The second block shows the different behavior for value types and reference types.

```
public readonly record struct Coords(int X, int Y);
```

```
// Value type: each variable holds its own copy
var point1 = new Coords(3, 4);
var point2 = point1;
Console.WriteLine($"point1: ({point1.X}, {point1.Y})");
Console.WriteLine($"point2: ({point2.X}, {point2.Y})");
// point1 and point2 are independent copies

// Reference type: both variables refer to the same object
var list1 = new List<int> { 1, 2, 3 };
var list2 = list1;
list2.Add(4);
Console.WriteLine($"list1 count: {list1.Count}"); // 4 — same object
```

All types ultimately derive from [System.Object](/en-us/dotnet/api/system.object). Value types derive from [System.ValueType](/en-us/dotnet/api/system.valuetype), which derives from `object`. This unified hierarchy is called the [Common Type System](../../../standard/base-types/common-type-system) (CTS). For more information about inheritance, see [Inheritance](../object-oriented/inheritance).

## Choose which kind of type

When you define a new type, the kind you choose shapes how your code behaves. Use the following guidelines to make an initial decision:

- **Tuple** — Temporary grouping of values that doesn't need a named type or behavior.
- **`struct`** or **`record struct`** — Small data (roughly 64 bytes or less), value semantics, or immutability. Record structs add value-based equality and `with` expressions.
- **`record class`** — Primarily data, with value-based equality, `ToString`, and nondestructive mutation. Supports inheritance.
- **`class`** — Complex behavior, polymorphism, or mutable state. Most custom types are classes.
- **`interface`** — A contract that unrelated types can implement. Defines capabilities rather than identity.
- **`enum`** — A fixed set of named constants, such as status codes or options.

More than one option is often reasonable.

## Compile-time type and run-time type

A variable can have different types at compile time and run time. The *compile-time type* is the declared or inferred type in source code. The *run-time type* is the actual type of the instance the variable refers to. The run-time type must be the same as the compile-time type, or a type that derives from it or implements it. An assignment is only valid when an implicit conversion exists from the run-time type to the compile-time type, such as an identity, reference, boxing, or numeric conversion.

```
// Compile-time and run-time types match:
string message = "Hello, world!";

// Compile-time type differs from run-time type:
object boxed = "This is a string at run time";
IEnumerable<char> characters = "abcdefghijklmnopqrstuvwxyz";
```

In the preceding example, `boxed` has a compile-time type of `object` but a run-time type of `string`. The assignment works because `string` derives from `object`. Similarly, `characters` has a compile-time type of `IEnumerable<char>`, and the assignment works because `string` implements that interface. The compile-time type controls overload resolution and available conversions. The run-time type controls virtual method dispatch, `is` expressions, and `switch` expressions.

## See also

- [Value types](../../language-reference/builtin-types/value-types)
- [Reference types](../../language-reference/keywords/reference-types)
- [Common Type System](../../../standard/base-types/common-type-system)

## C# language specification

For more information, see the [C# Language Specification](../../language-reference/language-specification/readme). The language specification is the definitive source for C# syntax and usage.

---

## Additional resources

---

- Last updated on 
  2026-03-26
