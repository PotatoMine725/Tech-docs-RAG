# C# classes - Microsoft Learn

Source: https://learn.microsoft.com/en-us/dotnet/csharp/fundamentals/types/classes

---

---

Note

Access to this page requires authorization. You can try [signing in](#) or changing directories.

Access to this page requires authorization. You can try changing directories.

# C# classes

Tip

**New to developing software?** Start with the [Get started](../../tour-of-csharp/tutorials/) tutorials first. You'll encounter classes once you need to model objects with behavior and state.

**Experienced in another language?** C# classes are similar to classes in Java or C++. Skim the [object initializers](#object-initializers) section for C#-specific patterns, and see [Records](records) for a data-focused alternative.

A *class* is a reference type that defines a blueprint for objects. When you create a variable of a class type, the variable holds a *reference* to an object on the managed heap. The variable doesn't hold the object data itself. Assigning a class variable to another variable copies the reference, so both variables point to the same object. Classes are the most common way to define custom types in C#. Use them when you need complex behavior, inheritance, or shared identity between references.

## When to use classes

Use a class when:

- The type has complex behavior or manages mutable state.
- You need inheritance to create a base class with derived specializations, or to create a derived type that extends an existing class.
- Instances represent a shared identity, not objects that happen to hold equal values. Two references to the same object should stay in sync.
- The type is large or long-lived and benefits from [heap allocation](../../../standard/garbage-collection/fundamentals#the-managed-heap) and reference semantics.

## Declare a class

Define a class with the `class` keyword followed by the type name. An optional [access modifier](../../language-reference/keywords/access-modifiers) controls visibility. The default is `internal`. Specify `public` to allow callers from other assemblies to use your types.

```
public class Customer
{
    public string Name { get; set; }

    public Customer(string name) => Name = name;
}
```

The class body contains fields, properties, methods, and events, collectively called *class members*. The name must be a valid C# [identifier name](../coding-style/identifier-names).

## Create objects

A class defines a type, but it isn't an object itself. You create an object (an *instance* of the class) with the `new` keyword:

```
var customer = new Customer("Allison");
Console.WriteLine(customer.Name); // Allison
```

The variable `customer` holds a reference to the object, not the object itself. You can assign multiple variables to the same object. Changes through one reference are visible through the other:

```
var c1 = new Customer("Grace");
var c2 = c1; // both variables reference the same object

c2.Name = "Hopper";
Console.WriteLine(c1.Name); // Hopper — c1 sees the change made through c2
```

This reference-sharing behavior is one distinction between classes and <structs>. With structs, assignment copies the data. More importantly, classes support [inheritance](#inheritance). You can build hierarchies where derived types reuse and specialize behavior from a base class. Structs can't participate in inheritance hierarchies. For more on the distinction, see [Value types and reference types](./#value-types-and-reference-types).

## Constructors and initialization

When you create an instance, you want its fields and properties initialized to useful values. C# offers several approaches: field initializers, constructor parameters, primary constructors, and required properties.

**[Field initializers](../../programming-guide/classes-and-structs/instance-constructors)** set a default value directly on the field declaration:

```
public class Container
{
    private int _capacity = 10;
}
```

Field initializers assign a reasonable default to a field or property. This distinguishes it from the following approaches where callers can provide the initial value.

**Constructor parameters** require callers to provide values:

```
public class Container
{
    private int _capacity;

    public Container(int capacity) => _capacity = capacity;
}
```

**[Primary constructors](../../whats-new/tutorials/primary-constructors)** (C# 12+) add parameters directly to the class declaration. Those parameters are available throughout the class body:

```
public class Container(int capacity)
{
    private int _capacity = capacity;
}
```

Primary constructors and field initializers can work together: the field initializer `_capacity = capacity` uses the primary-constructor parameter as its value. This pattern lets you capture constructor arguments in fields with a single, concise declaration.

**[Required properties](../../language-reference/keywords/required)** enforce that callers set specific properties through an object initializer:

```
public class Person
{
    public required string FirstName { get; set; }
    public required string LastName { get; set; }
}
```

```
// var missing = new Person(); // Error: required properties not set
var person = new Person { FirstName = "Grace", LastName = "Hopper" };
Console.WriteLine($"{person.FirstName} {person.LastName}"); // Grace Hopper
```

For a deeper look at constructor patterns, including parameter validation and constructor chaining, see [Constructors](../../programming-guide/classes-and-structs/constructors).

## Static classes

A `static` class can't be instantiated and contains only static members. Use static classes to organize utility methods that don't operate on instance data:

```
static class MathHelpers
{
    public static double CircleCircumference(double radius) =>
        2 * Math.PI * radius;
}
```

```
double circumference = MathHelpers.CircleCircumference(5.0);
Console.WriteLine($"Circumference: {circumference:F2}"); // Circumference: 31.42
```

The .NET class library includes many static classes, such as [Math](/en-us/dotnet/api/system.math) and [Console](/en-us/dotnet/api/system.console). A static class is implicitly sealed. You can't derive from it or instantiate it.

## Object initializers

*[Object initializers](../../programming-guide/classes-and-structs/object-and-collection-initializers)* let you set properties when you create an object, without writing a constructor for every combination of values:

```
class ConnectionOptions
{
    public string Host { get; init; } = "localhost";
    public int Port { get; init; } = 80;
    public bool UseSsl { get; init; }
}
```

```
var options = new ConnectionOptions
{
    Host = "db.example.com",
    Port = 5432,
    UseSsl = true
};
Console.WriteLine($"{options.Host}:{options.Port} (SSL: {options.UseSsl})");
// db.example.com:5432 (SSL: True)
```

Object initializers work with any accessible property that has a `set` or [`init`](../../language-reference/keywords/init) accessor. They combine naturally with `required` properties and with constructors that accept some parameters while letting the caller set others.

When the property is a *collection*, you can use a [Collection expressions (C# reference)](../../language-reference/operators/collection-expressions) to initialize that object.

## Inheritance

Classes support *inheritance*. You can define a new class that reuses, extends, or modifies the behavior of an existing class. The class you inherit from is the *base class*, and the new class is the *derived class*:

```
var manager = new Manager("Satya", "Engineering");
Console.WriteLine($"{manager.Name} manages {manager.Department}");
// Satya manages Engineering
```

A class can inherit from one base class and implement multiple interfaces. Derived classes inherit all members of the base class except constructors. For more information, see [Inheritance](../object-oriented/inheritance) and [Interfaces](interfaces).

## See also

- [Type system overview](./)
- [Structs](structs)
- [Records](records)
- [Interfaces](interfaces)
- [Inheritance](../object-oriented/inheritance)

---

## Additional resources

---

- Last updated on 
  2026-04-08
