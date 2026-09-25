# Hello World - Introductory tutorial - A tour of C# | Microsoft Learn

Source: https://learn.microsoft.com/en-us/dotnet/csharp/tour-of-csharp/tutorials/hello-world

---

---

Note

Access to this page requires authorization. You can try [signing in](#) or changing directories.

Access to this page requires authorization. You can try changing directories.

# Tutorial: Explore the C# language

This tutorial teaches you C#. You write your first C# program and see the results of compiling and running your code. It contains a series of lessons that begin with a "Hello World" program. These lessons teach you the fundamentals of the C# language.

Tip

**New to programming?** Start here - this tutorial assumes no prior experience. **Coming from another language?** You might prefer to skim the code samples and jump ahead to [Numbers in C#](numbers-in-csharp) or [Branches and loops](branches-and-loops).

In this tutorial, you:

- Launch a GitHub Codespace with a C# development environment.
- Create your first C# app.
- Create and use variables to store text data.
- Use runtime APIs with text data.

## Prerequisites

You must have one of the following options:

- A GitHub account to use [GitHub Codespaces](https://github.com/codespaces). If you don't already have one, you can create a free account at [GitHub.com](https://github.com).
- A computer with the following tools installed:
  - The [.NET 10 SDK](https://dotnet.microsoft.com/download/dotnet/10.0).
  - [Visual Studio Code](https://code.visualstudio.com/download).
  - The [C# DevKit](https://marketplace.visualstudio.com/items?itemName=ms-dotnettools.csdevkit).

## Open Codespaces

To start a GitHub Codespace with the tutorial environment, open a browser window to the [tutorial codespace](https://github.com/dotnet/tutorial-codespace) repository. Select the green *Code* button, and the *Codespaces* tab. Then select the `+` sign to create a new Codespace using this environment.

## Run your first program

1. When your codespace loads, create a new file in the *tutorials* folder named *hello-world.cs*.
2. Open your new file.
3. Type or copy the following code into *hello-world.cs*:

   ```
   Console.WriteLine("Hello, World!");
   ```
4. In the integrated terminal window, make the *tutorials* folder the current folder, and run your program:

   ```
   cd tutorials
   dotnet hello-world.cs
   ```

You ran your first C# program. It's a simple program that prints the message "Hello World!" It uses the [Console.WriteLine](/en-us/dotnet/api/system.console.writeline) method to print that message. `Console` is a type that represents the console window. `WriteLine` is a method of the `Console` type that prints a line of text to that text console.

Let's move on and explore more. The rest of this lesson explores working with the `string` type, which represents text in C#. Like the `Console` type, the `string` type has methods. The `string` methods work with text.

## Declare and use variables

Your first program prints the `string` "Hello World!" on the screen.

Tip

As you explore C# (or any programming language), you make mistakes when you write code. The **compiler** finds those errors and reports them to you. When the output contains error messages, look closely at the example code and the code in your `.cs` file to see what to fix. That exercise helps you learn the structure of C# code. You can also ask Copilot to find differences or spot mistakes.

Your first program is limited to printing one message. You can write more useful programs by using *variables*. A *variable* is a symbol you can use to run the same code with different values. Let's try it!

1. Start with the following code:

   ```
   string aFriend = "Bill";
   Console.WriteLine(aFriend);
   ```

   The first line declares a variable, `aFriend`, and assigns it a value, "Bill". The second line prints the name.
2. You can assign different values to any variable you declare. You can change the name to one of your friends. Add these two lines following the code you already added. Make sure you keep the declaration of the `aFriend` variable and its initial assignment.

   Important

   Don't delete the declaration of `aFriend`.
3. Add the following code at the end of the preceding code:

   ```
   aFriend = "Maira";
   Console.WriteLine(aFriend);
   ```

   Notice that the same line of code prints two different messages, based on the value stored in the `aFriend` variable. You might notice that the word "Hello" is missing in the last two messages. Let's fix that now.
4. Modify the lines that print the message to the following code:

   ```
   Console.WriteLine("Hello " + aFriend);
   ```
5. Run the app again by using `dotnet hello-world.cs` to see the results.

   You've been using `+` to build strings from **variables** and **constant** strings. There's a better way. You can place a variable between `{` and `}` characters to tell C# to replace that text with the value of the variable. This process is called [String interpolation](../../language-reference/tokens/interpolated).
6. If you add a `$` before the opening quote of the string, you can then include variables, like `aFriend`, inside the string between curly braces. Give it a try:

   ```
   Console.WriteLine($"Hello {aFriend}");
   ```
7. Run the app again by using `dotnet hello-world.cs` to see the results. Instead of "Hello {aFriend}", the message should be "Hello Maira".

## Work with strings

Your last edit was your first look at what you can do with strings. Let's explore more.

You're not limited to a single variable between the curly braces.

1. Try the following code at the bottom of your app:

   ```
   string firstFriend = "Maria";
   string secondFriend = "Sage";
   Console.WriteLine($"My friends are {firstFriend} and {secondFriend}");
   ```

   Strings are more than a collection of letters. You can find the length of a string by using `Length`. `Length` is a **property** of a string and it returns the number of characters in that string.
2. Add the following code at the bottom of your app:

   ```
   Console.WriteLine($"The name {firstFriend} has {firstFriend.Length} letters.");
   Console.WriteLine($"The name {secondFriend} has {secondFriend.Length} letters.");
   ```

Tip

Now is a good time to explore on your own. You learned that `Console.WriteLine()` writes text to the screen. You learned how to declare variables and concatenate strings together. Experiment in your code. Your editor has a feature called *IntelliSense* that makes suggestions for what you can do. Type a `.` after the `d` in `firstFriend`. You see a list of suggestions for properties and methods you can use.

You've been using a *method*, [Console.WriteLine](/en-us/dotnet/api/system.console.writeline), to print messages. A *method* is a block of code that implements some action. It has a name, so you can access it.

Tip

**Learn more:** Explore [strings](../../programming-guide/strings/) in depth, or read about [methods and program structure](../../fundamentals/program-structure/) in the C# Fundamentals section.

## Remove whitespace from strings

Suppose your strings have leading or trailing spaces that you don't want to display. You want to **trim** the spaces from the strings.
The [Trim](/en-us/dotnet/api/system.string.trim) method and related methods [TrimStart](/en-us/dotnet/api/system.string.trimstart) and [TrimEnd](/en-us/dotnet/api/system.string.trimend) perform this task. Use these methods to remove leading and trailing spaces.

1. Try the following code:

   ```
   string greeting = "      Hello World!       ";
   Console.WriteLine($"[{greeting}]");

   string trimmedGreeting = greeting.TrimStart();
   Console.WriteLine($"[{trimmedGreeting}]");

   trimmedGreeting = greeting.TrimEnd();
   Console.WriteLine($"[{trimmedGreeting}]");

   trimmedGreeting = greeting.Trim();
   Console.WriteLine($"[{trimmedGreeting}]");
   ```

The square brackets `[` and `]` help you visualize what the `Trim`, `TrimStart`, and `TrimEnd` methods do. The brackets show where whitespace starts and ends.

This sample reinforces a couple of important concepts for working with strings. The methods that manipulate strings return new string objects rather than making modifications in place. You can see that each call to any of the `Trim` methods returns a new string but doesn't change the original message.

## Search and replace text in strings

You can use other methods to work with a string. For example, you might use a search and replace command in an editor or word processor. The [Replace](/en-us/dotnet/api/system.string.replace) method does something similar in a string. It searches for a substring and replaces it with different text. The [Replace](/en-us/dotnet/api/system.string.replace) method takes two **parameters**. These parameters are the strings between the parentheses. The first string is the text to search for. The second string is the text to replace it with. Try it for yourself.

1. Add this code. Type it in to see the hints as you start typing `.Re` after the `sayHello` variable:

   ```
   string sayHello = "Hello World!";
   Console.WriteLine(sayHello);
   sayHello = sayHello.Replace("Hello", "Greetings");
   Console.WriteLine(sayHello);
   ```

   Two other useful methods make a string all caps or all lowercase. Try the following code.
2. Type it in to see how **IntelliSense** provides hints as you start to type `To`:

   ```
   Console.WriteLine(sayHello.ToUpper());
   Console.WriteLine(sayHello.ToLower());
   ```

   The other part of a *search and replace* operation is to find text in a string. You can use the [Contains](/en-us/dotnet/api/system.string.contains) method for searching. It tells you if a string contains a substring inside it.
3. Try the following code to explore [Contains](/en-us/dotnet/api/system.string.contains):

   ```
   string songLyrics = "You say goodbye, and I say hello";
   Console.WriteLine(songLyrics.Contains("goodbye"));
   Console.WriteLine(songLyrics.Contains("greetings"));
   ```

   The [Contains](/en-us/dotnet/api/system.string.contains) method returns a *boolean* value that tells you if the string you were searching for was found. A *boolean* stores either a `true` or a `false` value. When displayed as text output, they're capitalized: `True` and `False`, respectively. You learn more about *boolean* values in a later lesson.

## Challenge

Two similar methods, [StartsWith](/en-us/dotnet/api/system.string.startswith) and [EndsWith](/en-us/dotnet/api/system.string.endswith), also search for substrings in a string. These methods find a substring at the beginning or at the end of the string. Try to modify the previous sample to use [StartsWith](/en-us/dotnet/api/system.string.startswith) and [EndsWith](/en-us/dotnet/api/system.string.endswith) instead of [Contains](/en-us/dotnet/api/system.string.contains). Search for "You" or "goodbye" at the beginning of a string. Search for "hello" or "goodbye" at the end of a string.

Note

Watch your punctuation when you test for the text at the end of the string. If the string ends with a period, you must check for a string that ends with a period.

You should get `true` for starting with "You" and ending with "hello" and `false` for starting with or ending with "goodbye".

Did you come up with something like the following code (expand to see the answer):

```
string songLyrics = "You say goodbye, and I say hello";
Console.WriteLine(songLyrics.StartsWith("You"));
Console.WriteLine(songLyrics.StartsWith("goodbye"));

Console.WriteLine(songLyrics.EndsWith("hello"));
Console.WriteLine(songLyrics.EndsWith("goodbye"));
```

For further reading on the `string` type:

- [C# programming guide article on strings](../../programming-guide/strings/).
- [How to tips on working with strings](../../how-to/#working-with-strings).

## Cleanup resources

GitHub automatically deletes your Codespace after 30 days of inactivity. If you plan to explore more tutorials in this series, you can leave your Codespace provisioned. If you're ready to visit the [.NET site](https://dotnet.microsoft.com/download/dotnet) to download the .NET SDK, you can delete your Codespace. To delete your Codespace, open a browser window and navigate to [your Codespaces](https://github.com/codespaces). You should see a list of your codespaces in the window. Select the three dots (`...`) in the entry for the learn tutorial codespace and select "delete".

## Next steps

Continue to the next tutorial in this series, or explore related topics in C# Fundamentals:

[Explore numbers in C#](numbers-in-csharp)

- [Strings](../../programming-guide/strings/) — Learn more about the `string` type you used in this tutorial.
- [Methods and program structure](../../fundamentals/program-structure/) — Understand how C# programs are organized.
- [File-based apps](../../fundamentals/tutorials/file-based-programs) — Learn about the `dotnet run` command you used to run your code.

---

## Additional resources

---

- Last updated on 
  2026-02-23
