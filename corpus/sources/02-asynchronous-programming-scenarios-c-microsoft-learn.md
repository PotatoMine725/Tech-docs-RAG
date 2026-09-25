# Asynchronous programming scenarios - C# | Microsoft Learn

Source: https://learn.microsoft.com/en-us/dotnet/csharp/asynchronous-programming/async-scenarios

---

---

Note

Access to this page requires authorization. You can try [signing in](#) or changing directories.

Access to this page requires authorization. You can try changing directories.

# Asynchronous programming scenarios

If your code implements I/O-bound scenarios to support network data requests, database access, or file system read/writes, asynchronous programming is the best approach. You can also write asynchronous code for CPU-bound scenarios like expensive calculations.

C# has a language-level asynchronous programming model that allows you to easily write asynchronous code without having to juggle callbacks or conform to a library that supports asynchrony. The model follows what is known as the [Task-based asynchronous pattern (TAP)](../../standard/asynchronous-programming-patterns/task-based-asynchronous-pattern-tap).

## Explore the asynchronous programming model

The `Task` and `Task<T>` objects represent the core of asynchronous programming. These objects are used to model asynchronous operations by supporting the `async` and `await` keywords. In most cases, the model is fairly simple for both I/O-bound and CPU-bound scenarios. Inside an `async` method:

- **I/O-bound code** starts an operation represented by a `Task` or `Task<T>` object within the `async` method.
- **CPU-bound code** starts an operation on a background thread with the [Task.Run](/en-us/dotnet/api/system.threading.tasks.task.run) method.

In both cases, an active `Task` represents an asynchronous operation that might not be complete.

The `await` keyword is where the magic happens. It yields control to the caller of the method that contains the `await` expression, and ultimately allows the UI to be responsive or a service to be elastic. While [there are ways](../../standard/asynchronous-programming-patterns/task-based-asynchronous-pattern-tap) to approach asynchronous code other than by using the `async` and `await` expressions, this article focuses on the language-level constructs.

Note

Some examples presented in this article use the [System.Net.Http.HttpClient](/en-us/dotnet/api/system.net.http.httpclient) class to download data from a web service. In the example code, the `s_httpClient` object is a static field of type `Program` class:

`private static readonly HttpClient s_httpClient = new();`

For more information, see the [complete example code](#review-the-complete-example) at the end of this article.

### Review underlying concepts

When you implement asynchronous programming in your C# code, the compiler transforms your program into a state machine. This construct tracks various operations and state in your code, such as yielding execution when the code reaches an `await` expression, and resuming execution when a background job completes.

In terms of computer science theory, asynchronous programming is an implementation of the [Promise model of asynchrony](https://en.wikipedia.org/wiki/Futures_and_promises).

In the asynchronous programming model, there are several key concepts to understand:

- You can use asynchronous code for both I/O-bound and CPU-bound code, but the implementation is different.
- Asynchronous code uses `Task<T>` and `Task` objects as constructs to model work running in the background.
- The `async` keyword declares a method as an asynchronous method, which allows you to use the `await` keyword in the method body.
- When you apply the `await` keyword, the code suspends the calling method and yields control back to its caller until the task completes.
- You can only use the `await` expression in an asynchronous method.

### I/O-bound example: Download data from web service

In this example, when the user selects a button, the app downloads data from a web service. You don't want to block the UI thread for the app during the download process. The following code accomplishes this task:

```
s_downloadButton.Clicked += async (o, e) =>
{
    // This line will yield control to the UI as the request
    // from the web service is happening.
    //
    // The UI thread is now free to perform other work.
    var stringData = await s_httpClient.GetStringAsync(URL);
    DoSomethingWithData(stringData);
};
```

The code expresses the intent (downloading data asynchronously) without getting bogged down in interacting with `Task` objects.

### CPU-bound example: Run game calculation

In the next example, a mobile game inflicts damage on several agents on the screen in response to a button event. Performing the damage calculation can be expensive. Running the calculation on the UI thread can cause display and UI interaction issues during the calculation.

The best way to handle the task is to start a background thread to complete the work with the `Task.Run` method. The operation yields by using an `await` expression. The operation resumes when the task completes. This approach allows the UI to run smoothly while the work completes in the background.

```
static DamageResult CalculateDamageDone()
{
    return new DamageResult()
    {
        // Code omitted:
        //
        // Does an expensive calculation and returns
        // the result of that calculation.
    };
}

s_calculateButton.Clicked += async (o, e) =>
{
    // This line will yield control to the UI while CalculateDamageDone()
    // performs its work. The UI thread is free to perform other work.
    var damageResult = await Task.Run(() => CalculateDamageDone());
    DisplayDamage(damageResult);
};
```

The code clearly expresses the intent of the button `Clicked` event. It doesn't require managing a background thread manually, and it completes the task in a nonblocking manner.

## Recognize CPU-bound and I/O-bound scenarios

The previous examples demonstrate how to use the `async` modifier and `await` expression for I/O-bound and CPU-bound work. An example for each scenario showcases how the code is different based on where the operation is bound. To prepare for your implementation, you need to understand how to identify when an operation is I/O-bound or CPU-bound. Your implementation choice can greatly affect the performance of your code and potentially lead to misusing constructs.

There are two primary questions to address before you write any code:

| Question | Scenario | Implementation |
| --- | --- | --- |
| *Should the code wait for a result or action, such as data from a database?* | **I/O-bound** | Use the `async` modifier and `await` expression *without* the `Task.Run` method.    Avoid using the Task Parallel Library. |
| *Should the code run an expensive computation?* | **CPU-bound** | Use the `async` modifier and `await` expression, but spawn off the work on another thread with the `Task.Run` method. This approach addresses concerns with CPU responsiveness.    If the work is appropriate for concurrency and parallelism, also consider using the [Task Parallel Library](../../standard/parallel-programming/task-parallel-library-tpl). |

Always measure the execution of your code. You might discover that your CPU-bound work isn't costly enough compared with the overhead of context switches when multithreading. Every choice has tradeoffs. Pick the correct tradeoff for your situation.

## Explore other examples

The examples in this section demonstrate several ways you can write asynchronous code in C#. They cover a few scenarios you might encounter.

### Extract data from a network

The following code downloads HTML from a given URL and counts the number of times the string ".NET" occurs in the HTML. The code uses ASP.NET to define a Web API controller method, which performs the task and returns the count.

Note

If you plan on doing HTML parsing in production code, don't use regular expressions. Use a parsing library instead.

```
[HttpGet, Route("DotNetCount")]
static public async Task<int> GetDotNetCountAsync(string URL)
{
    // Suspends GetDotNetCountAsync() to allow the caller (the web server)
    // to accept another request, rather than blocking on this one.
    var html = await s_httpClient.GetStringAsync(URL);
    return Regex.Matches(html, @"\.NET").Count;
}
```

You can write similar code for a Universal Windows App and perform the counting task after a button press:

```
private readonly HttpClient _httpClient = new HttpClient();

private async void OnSeeTheDotNetsButtonClick(object sender, RoutedEventArgs e)
{
    // Capture the task handle here so we can await the background task later.
    var getDotNetFoundationHtmlTask = _httpClient.GetStringAsync("https://dotnetfoundation.org");

    // Any other work on the UI thread can be done here, such as enabling a Progress Bar.
    // It's important to do the extra work here before the "await" call,
    // so the user sees the progress bar before execution of this method is yielded.
    NetworkProgressBar.IsEnabled = true;
    NetworkProgressBar.Visibility = Visibility.Visible;

    // The await operator suspends OnSeeTheDotNetsButtonClick(), returning control to its caller.
    // This action is what allows the app to be responsive and not block the UI thread.
    var html = await getDotNetFoundationHtmlTask;
    int count = Regex.Matches(html, @"\.NET").Count;

    DotNetCountLabel.Text = $"Number of .NETs on dotnetfoundation.org: {count}";

    NetworkProgressBar.IsEnabled = false;
    NetworkProgressBar.Visibility = Visibility.Collapsed;
}
```

### Wait for multiple tasks to complete

In some scenarios, the code needs to retrieve multiple pieces of data concurrently. The `Task` APIs provide methods that enable you to write asynchronous code that performs a nonblocking wait on multiple background jobs:

- [Task.WhenAll](/en-us/dotnet/api/system.threading.tasks.task.whenall) method
- [Task.WhenAny](/en-us/dotnet/api/system.threading.tasks.task.whenany) method

The following example shows how you might grab `User` object data for a set of `userId` objects.

```
private static async Task<User> GetUserAsync(int userId)
{
    // Code omitted:
    //
    // Given a user Id {userId}, retrieves a User object corresponding
    // to the entry in the database with {userId} as its Id.

    await Task.Yield(); // Simulate asynchronous database retrieval
    return new User() { id = userId };
}

private static async Task<IEnumerable<User>> GetUsersAsync(IEnumerable<int> userIds)
{
    var getUserTasks = new List<Task<User>>();
    foreach (int userId in userIds)
    {
        getUserTasks.Add(GetUserAsync(userId));
    }

    return await Task.WhenAll(getUserTasks);
}
```

You can write this code more succinctly by using LINQ:

```
private static async Task<User[]> GetUsersByLINQAsync(IEnumerable<int> userIds)
{
    var getUserTasks = userIds.Select(id => GetUserAsync(id)).ToArray();
    return await Task.WhenAll(getUserTasks);
}
```

Although you write less code by using LINQ, exercise caution when mixing LINQ with asynchronous code. LINQ uses deferred (or lazy) execution, which means that without immediate evaluation, async calls don't happen until the sequence is enumerated.

The previous example is correct and safe, because it uses the [Enumerable.ToArray](/en-us/dotnet/api/system.linq.enumerable.toarray) method to immediately evaluate the LINQ query and store the tasks in an array. This approach ensures the `id => GetUserAsync(id)` calls execute immediately and all tasks start concurrently, just like the `foreach` loop approach. Always use [Enumerable.ToArray](/en-us/dotnet/api/system.linq.enumerable.toarray) or [Enumerable.ToList](/en-us/dotnet/api/system.linq.enumerable.tolist) when creating tasks with LINQ to ensure immediate execution and concurrent task execution. Here's an example that demonstrates using `ToList()` with `Task.WhenAny` to process tasks as they complete:

```
private static async Task ProcessTasksAsTheyCompleteAsync(IEnumerable<int> userIds)
{
    var getUserTasks = userIds.Select(id => GetUserAsync(id)).ToList();
    
    while (getUserTasks.Count > 0)
    {
        Task<User> completedTask = await Task.WhenAny(getUserTasks);
        getUserTasks.Remove(completedTask);
        
        User user = await completedTask;
        Console.WriteLine($"Processed user {user.id}");
    }
}
```

In this example, `ToList()` creates a list that supports the `Remove()` operation, allowing you to dynamically remove completed tasks. This pattern is particularly useful when you want to handle results as soon as they're available, rather than waiting for all tasks to complete.

Although you write less code by using LINQ, exercise caution when mixing LINQ with asynchronous code. LINQ uses deferred (or lazy) execution. Asynchronous calls don't happen immediately as they do in a `foreach` loop, unless you force the generated sequence to iterate with a call to the `.ToList()` or `.ToArray()` method.

You can choose between [Enumerable.ToArray](/en-us/dotnet/api/system.linq.enumerable.toarray) and [Enumerable.ToList](/en-us/dotnet/api/system.linq.enumerable.tolist) based on your scenario:

- Use `ToArray()` when you plan to process all tasks together, such as with `Task.WhenAll`. Arrays are efficient for scenarios where the collection size is fixed.
- Use `ToList()` when you need to dynamically manage tasks, such as with `Task.WhenAny` where you might remove completed tasks from the collection as they finish.

## Review considerations for asynchronous programming

With asynchronous programming, there are several details to keep in mind that can prevent unexpected behavior.

### Use await inside async() method body

When you use the `async` modifier, you should include one or more `await` expressions in the method body. If the compiler doesn't encounter an `await` expression, the method fails to yield. Although the compiler generates a warning, the code still compiles and the compiler runs the method. The state machine generated by the C# compiler for the asynchronous method doesn't accomplish anything, so the entire process is highly inefficient.

### Add "Async" suffix to asynchronous method names

The .NET style convention is to add the "Async" suffix to all asynchronous method names. This approach helps to more easily differentiate between synchronous and asynchronous methods. Certain methods that aren't explicitly called by your code (such as event handlers or web controller methods) don't necessarily apply in this scenario. Because these items aren't explicitly called by your code, using explicit naming isn't as important.

### Return 'async void' only from event handlers

Event handlers must declare `void` return types and can't use or return `Task` and `Task<T>` objects as other methods do. When you write asynchronous event handlers, you need to use the `async` modifier on a `void` returning method for the handlers. Other implementations of `async void` returning methods don't follow the TAP model and can present challenges:

- Exceptions thrown in an `async void` method can't be caught outside of that method
- `async void` methods are difficult to test
- `async void` methods can cause negative side effects if the caller isn't expecting them to be asynchronous

### Use caution with asynchronous lambdas in LINQ

It's important to use caution when you implement asynchronous lambdas in LINQ expressions. Lambda expressions in LINQ use deferred execution, which means the code can execute at an unexpected time. The introduction of blocking tasks into this scenario can easily result in a deadlock, if the code isn't written correctly. Moreover, the nesting of asynchronous code can also make it difficult to reason about the execution of the code. Async and LINQ are powerful, but these techniques should be used together as carefully and clearly as possible.

### Yield for tasks in a nonblocking manner

If your program needs the result of a task, write code that implements the `await` expression in a nonblocking manner. Blocking the current thread as a means to wait synchronously for a `Task` item to complete can result in deadlocks and blocked context threads. This programming approach can require more complex error-handling. The following table provides guidance on how access results from tasks in a nonblocking way:

| Task scenario | Current code | Replace with 'await' |
| --- | --- | --- |
| *Retrieve the result of a background task* | `Task.Wait` or `Task.Result` | `await` |
| *Continue when any task completes* | `Task.WaitAny` | `await Task.WhenAny` |
| *Continue when **all** tasks complete* | `Task.WaitAll` | `await Task.WhenAll` |
| *Continue after some amount of time* | `Thread.Sleep` | `await Task.Delay` |

### Consider using ValueTask type

When an asynchronous method returns a `Task` object, performance bottlenecks might be introduced in certain paths. Because `Task` is a reference type, a `Task` object is allocated from the heap. If a method declared with the `async` modifier returns a cached result or completes synchronously, the extra allocations can accrue significant time costs in performance critical sections of code. This scenario can become costly when the allocations occur in tight loops. For more information, see [generalized async return types](../language-reference/keywords/async#return-types).

### Understand when to set ConfigureAwait(false)

Developers often inquire about when to use the [Task.ConfigureAwait(Boolean)](/en-us/dotnet/api/system.threading.tasks.task.configureawait#system-threading-tasks-task-configureawait(system-boolean)) boolean. This API allows for a `Task` instance to configure the context for the state machine that implements any `await` expression. When the boolean isn't set correctly, performance can degrade or deadlocks can occur. For more information, see [ConfigureAwait FAQ](https://devblogs.microsoft.com/dotnet/configureawait-faq).

### Write less-stateful code

Avoid writing code that depends on the state of global objects or the execution of certain methods. Instead, depend only on the return values of methods. There are many benefits to writing code that is less-stateful:

- Easier to reason about code
- Easier to test code
- More simple to mix asynchronous and synchronous code
- Able to avoid race conditions in code
- Simple to coordinate asynchronous code that depends on return values
- (Bonus) Works well with dependency injection in code

A recommended goal is to achieve complete or near-complete [Referential Transparency](https://en.wikipedia.org/wiki/Referential_transparency) in your code. This approach results in a predictable, testable, and maintainable codebase.

### Synchronous access to asynchronous operations

In scenarios, you might need to block on asynchronous operations when the `await` keyword isn't available throughout your call stack. This situation occurs in legacy codebases or when integrating asynchronous methods into synchronous APIs that can't be changed.

Warning

Synchronous blocking on asynchronous operations can lead to deadlocks and should be avoided whenever possible. The preferred solution is to use `async`/`await` throughout your call stack.

When you must block synchronously on a `Task`, here are the available approaches, listed from most to least preferred:

- [Use GetAwaiter().GetResult()](#use-getawaitergetresult)
- [Use Task.Run for complex scenarios](#use-taskrun-for-complex-scenarios)
- [Use Wait() and Result](#use-wait-and-result)

#### Use GetAwaiter().GetResult()

The `GetAwaiter().GetResult()` pattern is generally the preferred approach when you must block synchronously:

```
// When you cannot use await
Task<string> task = GetDataAsync();
string result = task.GetAwaiter().GetResult();
```

This approach:

- Preserves the original exception without wrapping it in an `AggregateException`.
- Blocks the current thread until the task completes.
- Still carries deadlock risk if not used carefully.

#### Use Task.Run for complex scenarios

For complex scenarios where you need to isolate the asynchronous work:

```
// Offload to thread pool to avoid context deadlocks
string result = Task.Run(async () => await GetDataAsync()).GetAwaiter().GetResult();
```

This pattern:

- Executes the asynchronous method on a thread pool thread.
- Can help avoid some deadlock scenarios.
- Adds overhead by scheduling work to the thread pool.

#### Use Wait() and Result

You can use a blocking approach by calling [Wait()](/en-us/dotnet/api/system.threading.tasks.task.wait#system-threading-tasks-task-wait) and [Result](/en-us/dotnet/api/system.threading.tasks.task-1.result#system-threading-tasks-task-1-result). However, this approach is discouraged because it wraps exceptions in [AggregateException](/en-us/dotnet/api/system.aggregateexception).

```
Task<string> task = GetDataAsync();
task.Wait();
string result = task.Result;
```

Problems with `Wait()` and `Result`:

- Exceptions are wrapped in `AggregateException`, making error handling more complex.
- Higher deadlock risk.
- Less clear intent in code.

#### Additional considerations

- Deadlock prevention: Be especially careful in UI applications or when using a synchronization context.
- Performance impact: Blocking threads reduces scalability.
- Exception handling: Test error scenarios carefully as exception behavior differs between patterns.

For more detailed guidance on the challenges and considerations of synchronous wrappers for asynchronous methods, see [Should I expose synchronous wrappers for asynchronous methods?](https://devblogs.microsoft.com/pfxteam/should-i-expose-synchronous-wrappers-for-asynchronous-methods/).

## Review the complete example

The following code represents the complete example, which is available in the *Program.cs* example file.

```
using System.Text.RegularExpressions;
using System.Windows;
using Microsoft.AspNetCore.Mvc;

class Button
{
    public Func<object, object, Task>? Clicked
    {
        get;
        internal set;
    }
}

class DamageResult
{
    public int Damage
    {
        get { return 0; }
    }
}

class User
{
    public bool isEnabled
    {
        get;
        set;
    }

    public int id
    {
        get;
        set;
    }
}

public class Program
{
    private static readonly Button s_downloadButton = new();
    private static readonly Button s_calculateButton = new();

    private static readonly HttpClient s_httpClient = new();

    private static readonly IEnumerable<string> s_urlList = new string[]
    {
            "https://learn.microsoft.com",
            "https://learn.microsoft.com/aspnet/core",
            "https://learn.microsoft.com/azure",
            "https://learn.microsoft.com/azure/devops",
            "https://learn.microsoft.com/dotnet",
            "https://learn.microsoft.com/dotnet/desktop/wpf/get-started/create-app-visual-studio",
            "https://learn.microsoft.com/education",
            "https://learn.microsoft.com/shows/net-core-101/what-is-net",
            "https://learn.microsoft.com/enterprise-mobility-security",
            "https://learn.microsoft.com/gaming",
            "https://learn.microsoft.com/graph",
            "https://learn.microsoft.com/microsoft-365",
            "https://learn.microsoft.com/office",
            "https://learn.microsoft.com/powershell",
            "https://learn.microsoft.com/sql",
            "https://learn.microsoft.com/surface",
            "https://dotnetfoundation.org",
            "https://learn.microsoft.com/visualstudio",
            "https://learn.microsoft.com/windows",
            "https://learn.microsoft.com/maui"
    };

    private static void Calculate()
    {
        static DamageResult CalculateDamageDone()
        {
            return new DamageResult()
            {
                // Code omitted:
                //
                // Does an expensive calculation and returns
                // the result of that calculation.
            };
        }

        s_calculateButton.Clicked += async (o, e) =>
        {
            // This line will yield control to the UI while CalculateDamageDone()
            // performs its work. The UI thread is free to perform other work.
            var damageResult = await Task.Run(() => CalculateDamageDone());
            DisplayDamage(damageResult);
        };
    }

    private static void DisplayDamage(DamageResult damage)
    {
        Console.WriteLine(damage.Damage);
    }

    private static void Download(string URL)
    {
        s_downloadButton.Clicked += async (o, e) =>
        {
            // This line will yield control to the UI as the request
            // from the web service is happening.
            //
            // The UI thread is now free to perform other work.
            var stringData = await s_httpClient.GetStringAsync(URL);
            DoSomethingWithData(stringData);
        };
    }

    private static void DoSomethingWithData(object stringData)
    {
        Console.WriteLine($"Displaying data: {stringData}");
    }

    private static async Task<User> GetUserAsync(int userId)
    {
        // Code omitted:
        //
        // Given a user Id {userId}, retrieves a User object corresponding
        // to the entry in the database with {userId} as its Id.

        await Task.Yield(); // Simulate asynchronous database retrieval
        return new User() { id = userId };
    }

    private static async Task<IEnumerable<User>> GetUsersAsync(IEnumerable<int> userIds)
    {
        var getUserTasks = new List<Task<User>>();
        foreach (int userId in userIds)
        {
            getUserTasks.Add(GetUserAsync(userId));
        }

        return await Task.WhenAll(getUserTasks);
    }

    private static async Task<User[]> GetUsersByLINQAsync(IEnumerable<int> userIds)
    {
        var getUserTasks = userIds.Select(id => GetUserAsync(id)).ToArray();
        return await Task.WhenAll(getUserTasks);
    }

    private static async Task ProcessTasksAsTheyCompleteAsync(IEnumerable<int> userIds)
    {
        var getUserTasks = userIds.Select(id => GetUserAsync(id)).ToList();
        
        while (getUserTasks.Count > 0)
        {
            Task<User> completedTask = await Task.WhenAny(getUserTasks);
            getUserTasks.Remove(completedTask);
            
            User user = await completedTask;
            Console.WriteLine($"Processed user {user.id}");
        }
    }

    [HttpGet, Route("DotNetCount")]
    static public async Task<int> GetDotNetCountAsync(string URL)
    {
        // Suspends GetDotNetCountAsync() to allow the caller (the web server)
        // to accept another request, rather than blocking on this one.
        var html = await s_httpClient.GetStringAsync(URL);
        return Regex.Matches(html, @"\.NET").Count;
    }

    static async Task Main()
    {
        Console.WriteLine("Application started.");

        Console.WriteLine("Counting '.NET' phrase in websites...");
        int total = 0;
        foreach (string url in s_urlList)
        {
            var result = await GetDotNetCountAsync(url);
            Console.WriteLine($"{url}: {result}");
            total += result;
        }
        Console.WriteLine("Total: " + total);

        Console.WriteLine("Retrieving User objects with list of IDs...");
        IEnumerable<int> ids = new int[] { 1, 2, 3, 4, 5, 6, 7, 8, 9, 0 };
        var users = await GetUsersAsync(ids);
        foreach (User? user in users)
        {
            Console.WriteLine($"{user.id}: isEnabled={user.isEnabled}");
        }

        Console.WriteLine("Processing tasks as they complete...");
        await ProcessTasksAsTheyCompleteAsync(ids);

        Console.WriteLine("Application ending.");
    }
}

// Example output:
//
// Application started.
// Counting '.NET' phrase in websites...
// https://learn.microsoft.com: 0
// https://learn.microsoft.com/aspnet/core: 57
// https://learn.microsoft.com/azure: 1
// https://learn.microsoft.com/azure/devops: 2
// https://learn.microsoft.com/dotnet: 83
// https://learn.microsoft.com/dotnet/desktop/wpf/get-started/create-app-visual-studio: 31
// https://learn.microsoft.com/education: 0
// https://learn.microsoft.com/shows/net-core-101/what-is-net: 42
// https://learn.microsoft.com/enterprise-mobility-security: 0
// https://learn.microsoft.com/gaming: 0
// https://learn.microsoft.com/graph: 0
// https://learn.microsoft.com/microsoft-365: 0
// https://learn.microsoft.com/office: 0
// https://learn.microsoft.com/powershell: 0
// https://learn.microsoft.com/sql: 0
// https://learn.microsoft.com/surface: 0
// https://dotnetfoundation.org: 16
// https://learn.microsoft.com/visualstudio: 0
// https://learn.microsoft.com/windows: 0
// https://learn.microsoft.com/maui: 6
// Total: 238
// Retrieving User objects with list of IDs...
// 1: isEnabled= False
// 2: isEnabled= False
// 3: isEnabled= False
// 4: isEnabled= False
// 5: isEnabled= False
// 6: isEnabled= False
// 7: isEnabled= False
// 8: isEnabled= False
// 9: isEnabled= False
// 0: isEnabled= False
// Application ending.
```

## Related links

- [The Task asynchronous programming model (C#)](task-asynchronous-programming-model)

---

## Additional resources

---

- Last updated on 
  2025-08-15
