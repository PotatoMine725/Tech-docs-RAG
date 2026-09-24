# C# Keywords and contextual keywords - C# reference - Microsoft Learn

Source: https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/keywords/

---

---

Note

Access to this page requires authorization. You can try [signing in](#) or changing directories.

Access to this page requires authorization. You can try changing directories.

# C# keywords

Keywords are predefined, reserved identifiers that have special meanings to the compiler. You can't use them as identifiers in your program unless you prefix them with `@`. For example, `@if` is a valid identifier, but `if` isn't because `if` is a keyword.

The C# language reference documents the most recently released version of the C# language. It also contains initial documentation for features in public previews for the upcoming language release.

The documentation identifies any feature first introduced in the last three versions of the language or in current public previews.

Tip

To find when a feature was first introduced in C#, consult the article on the [C# language version history](../../whats-new/csharp-version-history).

The first table in this article lists keywords that are reserved identifiers in any part of a C# program. The second table lists the contextual keywords in C#. Contextual keywords have special meaning only in a limited program context and can be used as identifiers outside that context. Generally, as new keywords are added to the C# language, they're added as contextual keywords to avoid breaking programs written in earlier versions.

[`abstract`](abstract)  
[`as`](../operators/type-testing-and-cast#the-as-operator)  
[`base`](base)  
[`bool`](../builtin-types/bool)  
[`break`](../statements/jump-statements#the-break-statement)  
[`byte`](../builtin-types/integral-numeric-types)  
[`case`](../statements/selection-statements#the-switch-statement)  
[`catch`](../statements/exception-handling-statements#the-try-catch-statement)  
[`char`](../builtin-types/char)  
[`checked`](../statements/checked-and-unchecked)  
[`class`](class)  
[`const`](const)  
[`continue`](../statements/jump-statements#the-continue-statement)  
[`decimal`](../builtin-types/floating-point-numeric-types)  
[`default`](default)  
[`delegate`](../builtin-types/reference-types)  
[`do`](../statements/iteration-statements#the-do-statement)  
[`double`](../builtin-types/floating-point-numeric-types)  
[`else`](../statements/selection-statements#the-if-statement)  
[`enum`](../builtin-types/enum)

[`event`](event)  
[`explicit`](../operators/user-defined-conversion-operators)  
[`extern`](extern)  
[`false`](../builtin-types/bool)  
[`finally`](../statements/exception-handling-statements#the-try-finally-statement)  
[`fixed`](../statements/fixed)  
[`float`](../builtin-types/floating-point-numeric-types)  
[`for`](../statements/iteration-statements#the-for-statement)  
[`foreach`](../statements/iteration-statements#the-foreach-statement)  
[`goto`](../statements/jump-statements#the-goto-statement)  
[`if`](../statements/selection-statements#the-if-statement)  
[`implicit`](../operators/user-defined-conversion-operators)  
[`in`](in)  
[`int`](../builtin-types/integral-numeric-types)  
[`interface`](interface)  
[`internal`](internal)  
[`is`](../operators/is)  
[`lock`](../statements/lock)  
[`long`](../builtin-types/integral-numeric-types)

[`namespace`](namespace)  
[`new`](new)  
[`null`](null)  
[`object`](../builtin-types/reference-types)  
[`operator`](../operators/operator-overloading)  
[`out`](out)  
[`override`](override)  
[`params`](method-parameters#params-modifier)  
[`private`](private)  
[`protected`](protected)  
[`public`](public)  
[`readonly`](readonly)  
[`ref`](ref)  
[`return`](../statements/jump-statements#the-return-statement)  
[`sbyte`](../builtin-types/integral-numeric-types)  
[`sealed`](sealed)  
[`short`](../builtin-types/integral-numeric-types)  
[`sizeof`](../operators/sizeof)  
[`stackalloc`](../operators/stackalloc)

[`static`](static)  
[`string`](../builtin-types/reference-types)  
[`struct`](../builtin-types/struct)  
[`switch`](../operators/switch-expression)  
[`this`](this)  
[`throw`](../statements/exception-handling-statements#the-throw-statement)  
[`true`](../builtin-types/bool)  
[`try`](../statements/exception-handling-statements#the-try-statement)  
[`typeof`](../operators/type-testing-and-cast#the-typeof-operator)  
[`uint`](../builtin-types/integral-numeric-types)  
[`ulong`](../builtin-types/integral-numeric-types)  
[`unchecked`](../statements/checked-and-unchecked)  
[`unsafe`](unsafe)  
[`ushort`](../builtin-types/integral-numeric-types)  
[`using`](using)  
[`virtual`](virtual)  
[`void`](../builtin-types/void)  
[`volatile`](volatile)  
[`while`](../statements/iteration-statements#the-while-statement)

## Contextual keywords

A contextual keyword provides a specific meaning in the code, but it isn't a reserved word in C#. Some contextual keywords, such as `partial` and `where`, have special meanings in two or more contexts.

[`add`](add)  
[`allows`](where-generic-type-constraint)  
[`alias`](extern-alias)  
[`and`](../operators/patterns#logical-patterns)  
[`ascending`](ascending)  
[`args`](../../fundamentals/program-structure/top-level-statements#args)  
[`async`](async)  
[`await`](../operators/await)  
[`by`](by)  
[`closed`](closed)  
[`descending`](descending)  
[`dynamic`](../builtin-types/reference-types)  
[`equals`](equals)

[`extension`](extension)  
[`field`](field)  
[`file`](file)  
[`from`](from-clause)  
[`get`](get)  
[`global`](../operators/namespace-alias-qualifier)  
[`group`](group-clause)  
[`init`](init)  
[`into`](into)  
[`join`](join-clause)  
[`let`](let-clause)  
[`managed` (function pointer calling convention)](../unsafe-code#function-pointers)  
[`nameof`](../operators/nameof)

[`nint`](../builtin-types/integral-numeric-types)  
[`not`](../operators/patterns#logical-patterns)  
[`notnull`](../../programming-guide/generics/constraints-on-type-parameters#notnull-constraint)  
[`nuint`](../builtin-types/integral-numeric-types)  
[`on`](on)  
[`or`](../operators/patterns#logical-patterns)  
[`orderby`](orderby-clause)  
[`partial` (type)](partial-type)  
[`partial` (member)](partial-member)  
[`record`](../../fundamentals/types/records)  
[`remove`](remove)  
[`required`](required)  
[`safe`](safe)

[`scoped`](../statements/declarations#scoped-ref)  
[`select`](select-clause)  
[`set`](set)  
[`unmanaged` (function pointer calling convention)](../unsafe-code#function-pointers)  
[`unmanaged` (generic type constraint)](../../programming-guide/generics/constraints-on-type-parameters#unmanaged-constraint)  
[`value`](value)  
[`var`](../statements/declarations#implicitly-typed-local-variables)  
[`when` (filter condition)](when)  
[`where` (generic type constraint)](where-generic-type-constraint)  
[`where` (query clause)](where-clause)  
[`with`](with)  
[`yield`](../statements/yield)

---

## Additional resources

---

- Last updated on 
  2026-06-05
