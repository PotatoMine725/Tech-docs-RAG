# Judge spot-check: owner grading sheet (blind)

EVAL-004a, ledger row 11 (self-preference mitigation: the judge is the same model as the answer model).
Grade each item yourself **before** opening `judge-spot-check-judge.md`. That file holds the judge's verdicts
and the S-id → case / arm mapping. This file shows no label, no judge verdict and no arm.

Grade with the judge's own rules (`config/prompts/judge_v1.md`), using only the ground truth and the cited
passages shown, not your own knowledge:
- **Answer check** (answerable question). Per required point: `yes` / `partial` / `no`. Contradicts ground truth or
  states a MUST-NOT-CLAIM item: `true` / `false`. Unsupported claims: quote them, or write `none`. Per citation
  marker: does the passage support the claim it is attached to: `yes` / `partial` / `no`.
- **Refusal check** (question the documents do not answer). `presents_related_as_answer` is `true` if the
  response presents related content, or an inferred technique, as the documents' answer, makes a substantive
  answering claim, or never says the topic isn't covered; otherwise `false`.

Sample: 10 judged records, seed 42, stratified by arm and result label (rule in
`docs/reports/execution/EVAL-004a.md`). Owner columns are empty on purpose.

## S01 (answer check)

**Question** (en):

> In ASP.NET Core, what is the difference between how a conventional middleware and a middleware that implements IMiddleware get a scoped DbContext, and what extra setup does the IMiddleware one need in the app?

**Ground truth**

- Expected answer: Conventional middleware receives the scoped service (SampleDbContext in the example) as a parameter of InvokeAsync. Factory-activated middleware implements IMiddleware and receives the scoped service through its constructor, because IMiddleware is activated per client request (connection). The factory-activated middleware is registered as a scoped or transient service in the service container; UseMiddleware sees that the type implements IMiddleware and resolves it with the registered IMiddlewareFactory.
- P1 (required): Conventional middleware receives the scoped service (SampleDbContext in the example) as a parameter of InvokeAsync.
- P2 (required): Factory-activated middleware implements IMiddleware and receives the scoped service through its constructor, because IMiddleware is activated per client request (connection).
- P3 (required): The factory-activated middleware is registered as a scoped or transient service in the service container; UseMiddleware sees that the type implements IMiddleware and resolves it with the registered IMiddlewareFactory.
- P4 (optional, context only): Benefits: activation per client request (injection of scoped services) and strong typing.
- Acceptable variations: "MiddlewareFactory" (the default IMiddlewareFactory) may be named.
- MUST-NOT-CLAIM: Factory-activated middleware is registered as a singleton.; Conventional middleware takes scoped services in its constructor.
- Citation criteria: One citation per slot: S1 from the #11 intro (any variant, including text under 'Additional resources') for P2/P3; S2 from #11 'IMiddleware' (the conventional InvokeAsync signature) or #10 'Service lifetimes' for P1.

**Answer**:

> For convention-based middleware, a scoped service like a `DbContext` can be injected directly into the `InvokeAsync` method parameter (for example, `SampleDbContext dbContext` or `AppDbContext db`) [3][5]. For factory-based middleware that implements `IMiddleware`, `IMiddleware` is activated per client request (connection), which allows scoped services to be injected directly into the middleware's constructor [1][2][4].

**Note about missing information**:

> The context does not state what extra setup `IMiddleware` needs in the app, other than noting that the `IMiddlewareFactory` instance is registered in the container and the middleware is registered as a scoped or transient service.

**Cited passages** (5):

[3] #11 — Factory-based middleware activation in ASP.NET Core > IMiddleware

> ## IMiddleware
>
> [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) defines middleware for the app's request pipeline. The [InvokeAsync(HttpContext, RequestDelegate)](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware.invokeasync) method handles requests and returns a [Task](/en-us/dotnet/api/system.threading.tasks.task) that represents the execution of the middleware.
>
> Middleware activated by convention:
>
> ```
> public class ConventionalMiddleware
> {
>     private readonly RequestDelegate _next;
>
>     public ConventionalMiddleware(RequestDelegate next)
>         => _next = next;
>
>     public async Task InvokeAsync(HttpContext context, SampleDbContext dbContext)
>     {
>         var keyValue = context.Request.Query["key"];
>
>         if (!string.IsNullOrWhiteSpace(keyValue))
>         {
>             dbContext.Requests.Add(new Request("Conventional", keyValue));
>
>             await dbContext.SaveChangesAsync();
>         }
>
>         await _next(context);
>     }
> }
> ```
>
> Middleware activated by [MiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.middlewarefactory):

[5] #11 — Factory-based middleware activation in ASP.NET Core > IMiddleware

> ## IMiddleware
>
> [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) defines middleware for the app's request pipeline. The [InvokeAsync(HttpContext, RequestDelegate)](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware.invokeasync) method handles requests and returns a [Task](/en-us/dotnet/api/system.threading.tasks.task) that represents the execution of the middleware.
>
> Middleware activated by convention:
>
> ```
> public class ConventionalMiddleware
> {
>     private readonly RequestDelegate _next;
>
>     public ConventionalMiddleware(RequestDelegate next)
>     {
>         _next = next;
>     }
>
>     public async Task InvokeAsync(HttpContext context, AppDbContext db)
>     {
>         var keyValue = context.Request.Query["key"];
>
>         if (!string.IsNullOrWhiteSpace(keyValue))
>         {
>             db.Add(new Request()
>                 {
>                     DT = DateTime.UtcNow, 
>                     MiddlewareActivation = "ConventionalMiddleware", 
>                     Value = keyValue
>                 });
>
>             await db.SaveChangesAsync();
>         }
>
>         await _next(context);
>     }
> }
> ```
>
> Middleware activated by [MiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.middlewarefactory):

[1] #11 — Factory-based middleware activation in ASP.NET Core > Additional resources

> ## Additional resources
>
> - [ASP.NET Core middleware](./?view=aspnetcore-10.0)
> - [Middleware activation with a third-party container in ASP.NET Core](extensibility-third-party-container?view=aspnetcore-10.0)
>
> [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory)/[IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is an extensibility point for [middleware](./?view=aspnetcore-10.0) activation.
>
> [UseMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.builder.usemiddlewareextensions.usemiddleware) extension methods check if a middleware's registered type implements [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware). If it does, the [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) instance registered in the container is used to resolve the [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) implementation instead of using the convention-based middleware activation logic. The middleware is registered as a [scoped or transient service](../dependency-injection?view=aspnetcore-10.0#service-lifetimes) in the app's service container.
>
> Benefits:
>
> - Activation per client request (injection of scoped services)
> - Strong typing of middleware
>
> [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is activated per client request (connection), so scoped services can be injected into the middleware's constructor.

[2] #11 — Factory-based middleware activation in ASP.NET Core

> # Factory-based middleware activation in ASP.NET Core
>
> [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory)/[IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is an extensibility point for [middleware](./?view=aspnetcore-10.0) activation that offers the following benefits:
>
> - Activation per client request (injection of scoped services)
> - Strong typing of middleware
>
> [UseMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.builder.usemiddlewareextensions.usemiddleware) extension methods check if a middleware's registered type implements [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware). If it does, the [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) instance registered in the container is used to resolve the [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) implementation instead of using the convention-based middleware activation logic. The middleware is registered as a [scoped or transient service](../dependency-injection?view=aspnetcore-10.0#service-lifetimes) in the app's service container.
>
> [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is activated per client request (connection), so scoped services can be injected into the middleware's constructor.

[4] #11 — Factory-based middleware activation in ASP.NET Core > Additional resources

> middleware
>
> [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is activated per client request (connection), so scoped services can be injected into the middleware's constructor.
>
> [View or download sample code](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/middleware/extensibility/samples) ([how to download](../?view=aspnetcore-10.0#how-to-download-a-sample))

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| P1 covered |  |  |
| P2 covered |  |  |
| P3 covered |  |  |
| contradicts ground truth |  |  |
| unsupported claims |  |  |
| citation [3] supports its claim |  |  |
| citation [5] supports its claim |  |  |
| citation [1] supports its claim |  |  |
| citation [2] supports its claim |  |  |
| citation [4] supports its claim |  |  |
| agree with the judge? (fill after opening the key) |  |  |

## S02 (refusal check)

**Question** (en):

> What does scope validation check in ASP.NET Core dependency injection, and when is it enabled?

**Ground truth**

- Expected answer: The assistant should explicitly state that the provided collection does not contain sufficient information.
- Acceptable variations: The refusal may say the documents only link to other pages about it.
- MUST-NOT-CLAIM: What scope validation checks, which exception it throws, or in which environment it is enabled, presented as from the documents.
- Citation criteria: Citing the #10 'Scope validation' links as evidence for an answer = hallucination.

**Answer**:

> The document collection does not contain enough information to answer this question.

**Note about missing information**:

> The provided context mentions 'Scope validation' under headings and resources, but does not explain what scope validation checks or when it is enabled.

**Cited passages** (2):

[1] #10 — Dependency injection in ASP.NET Core > Lifetime and registration options

> .OperationId}");
>         _logger.LogInformation($"Singleton: {_singletonOperation.OperationId}");
>
>         await _next(context);
>     }
> }
> ```
>
> In the app processing pipeline of the `Program` file (.NET 6 or later) or the `Startup.Configure` method (.NET 5 or earlier):
>
> ```
> app.UseMiddleware<MyMiddleware>();
> ```
>
> For more information on creating middleware, see [Write custom ASP.NET Core middleware](middleware/write?view=aspnetcore-10.0).
>
> Output from the preceding examples shows:
>
> - *Transient* objects are always different. The transient `OperationId` value is different for the Razor component and in the middleware.
> - *Scoped* objects are the same for a given request but differ across new Blazor circuits.
> - *Singleton* objects are the same for every request or Blazor circuit.
>
> - *Transient* objects are always different. The transient `OperationId` value is different for the page and in the middleware.
> - *Scoped* objects are the same for a given request but differ across new requests.
> - *Singleton* objects are the same for every request.
>
> ## Resolve a service at app startup
>
> The following code shows how to resolve a scoped service for a limited duration when the app starts:
>
> ```
> var app = builder.Build();
>
> using (var serviceScope = app.Services.CreateScope())
> {
>     var services = serviceScope.ServiceProvider;
>     var dependency = services.GetRequiredService<IMyDependency>();
>     dependency.WriteMessage("Call services from main");
> }
> ```
>
> ## Scope validation
>
> For guidance on scope validation, see the following resources:
>
> - [.NET dependency injection: Scope validation](/en-us/d

[2] #10 — Dependency injection in ASP.NET Core > Resolve a service at app startup

> dependency.WriteMessage("Call services from main");
> }
> ```
>
> ## Scope validation
>
> For guidance on scope validation, see the following resources:
>
> - [.NET dependency injection: Scope validation](/en-us/dotnet/core/extensions/dependency-injection/overview#scope-validation)
> - [ASP.NET Core Web Host: Scope validation](host/web-host?view=aspnetcore-10.0#scope-validation)
>
> ## Request Services
>
> Services and their dependencies within an ASP.NET Core request are exposed through [HttpContext.RequestServices](/en-us/dotnet/api/microsoft.aspnetcore.http.httpcontext.requestservices#microsoft-aspnetcore-http-httpcontext-requestservices).
>
> The framework creates a scope per request, and `RequestServices` exposes the scoped service provider. All scoped services are valid for as long as the request is active.
>
> Note
>
> Prefer requesting dependencies as constructor parameters over resolving services from `RequestServices`. Requesting dependencies as constructor parameters yields classes that are easier to test.
>
> ## Design services for dependency injection
>
> When designing services for DI:
>
> - Avoid stateful, static classes and members. Avoid creating global state by designing apps to use singleton services instead.
> - Avoid direct instantiation of dependent classes within services. Direct instantiation couples the code to a particular implementation.
> - Make services small, well-factored, and easily tested.
>
> If a class has many injected dependencies, it might be a sign that the class has too many responsibilities and violates the [Single Responsibility Principle (SRP)](/en-us/dotnet/standard/modern-we

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| presents_related_as_answer |  |  |
| agree with the judge? (fill after opening the key) |  |  |

## S03 (answer check)

**Question** (vi):

> Mình gắn `[ValidatableType]` cho một model class khai báo private, lồng bên trong một class khác. App vẫn build được nhưng validation cho model đó không bao giờ chạy. Nguyên nhân là gì và sửa thế nào?

**Ground truth**

- Expected answer: The validation source generator emits code in a separate file, so it can't access a type (or one of its containing types) that is private or file-local. In that case the generator silently skips validation for the type (diagnostic ASP0033). Fix: make the attributed type and each of its containing types public or internal.
- P1 (required): The validation source generator emits code in a separate file, so it can't access a type (or one of its containing types) that is private or file-local.
- P2 (required): In that case the generator silently skips validation for the type (diagnostic ASP0033).
- P3 (required): Fix: make the attributed type and each of its containing types public or internal.
- P4 (optional, context only): ASP0033 is a Usage rule with severity Warning.
- Acceptable variations: The fix may be shown as changing `file sealed class` to `internal sealed class`.
- MUST-NOT-CLAIM: The type must be public (wrong: internal is also allowed).; ASP0033 is a build error.
- Citation criteria: The cited chunk contains the "silently skips validation" sentence and/or the public-or-internal fix.

**Answer**:

> Nguyên nhân là do thuộc tính `[ValidatableType]` được áp dụng cho một kiểu dữ liệu mà bộ tạo nguồn xác thực (validation source generator) không thể truy cập được, chẳng hạn như khi kiểu dữ liệu đó hoặc một trong các kiểu chứa nó là private hoặc file-local [1]. Để khắc phục vi phạm này, bạn cần làm cho kiểu dữ liệu được gắn thuộc tính và mỗi kiểu chứa nó trở thành public hoặc internal [2].

**Cited passages** (2):

[1] #29 — ASP0033: `[ValidatableType]` is applied to an inaccessible type > Cause

> ## Cause
>
> The <xref:Microsoft.Extensions.Validation.ValidatableTypeAttribute> attribute is applied to a type that the validation source generator can't access. The type, or one of its containing types, is private or file-local.
>
> ## Rule description
>
> The validation source generator emits code in a separate file. A validatable type and all of its containing types must be public or internal and can't be file-local. Otherwise, the generator silently skips validation for the type.
>
> The following code produces this diagnostic:
>
> ```csharp
> [ValidatableType]
> file sealed class Asp0033FileLocalValidatableType
> {
>     [Required]
>     public string Name { get; set; } = string.Empty;
> }
> ```

[2] #29 — ASP0033: `[ValidatableType]` is applied to an inaccessible type > How to fix violations

> ## How to fix violations
>
> Make the attributed type and each of its containing types public or internal. For example, change `Asp0033FileLocalValidatableType` to an internal type:
>
> ```csharp
> [ValidatableType]
> internal sealed class Asp0033FileLocalValidatableType
> {
>     [Required]
>     public string Name { get; set; } = string.Empty;
> }
> ```
>
> For more information, see <xref:fundamentals/validation>.

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| P1 covered |  |  |
| P2 covered |  |  |
| P3 covered |  |  |
| contradicts ground truth |  |  |
| unsupported claims |  |  |
| citation [1] supports its claim |  |  |
| citation [2] supports its claim |  |  |
| agree with the judge? (fill after opening the key) |  |  |

## S04 (refusal check)

**Question** (en):

> What does scope validation check in ASP.NET Core dependency injection, and when is it enabled?

**Ground truth**

- Expected answer: The assistant should explicitly state that the provided collection does not contain sufficient information.
- Acceptable variations: The refusal may say the documents only link to other pages about it.
- MUST-NOT-CLAIM: What scope validation checks, which exception it throws, or in which environment it is enabled, presented as from the documents.
- Citation criteria: Citing the #10 'Scope validation' links as evidence for an answer = hallucination.

**Answer**:

> The document collection does not contain enough information to answer this question.

**Note about missing information**:

> The provided context mentions scope validation under resources and guidance, but it does not state what scope validation checks or when it is enabled.

**Cited passages** (1):

[1] #10 — Dependency injection in ASP.NET Core > Scope validation

> ## Scope validation
>
> For guidance on scope validation, see the following resources:
>
> - [.NET dependency injection: Scope validation](/en-us/dotnet/core/extensions/dependency-injection/overview#scope-validation)
> - [ASP.NET Core Web Host: Scope validation](host/web-host?view=aspnetcore-10.0#scope-validation)
>
> ## Request Services
>
> Services and their dependencies within an ASP.NET Core request are exposed through [HttpContext.RequestServices](/en-us/dotnet/api/microsoft.aspnetcore.http.httpcontext.requestservices#microsoft-aspnetcore-http-httpcontext-requestservices).
>
> The framework creates a scope per request, and `RequestServices` exposes the scoped service provider. All scoped services are valid for as long as the request is active.
>
> Note
>
> Prefer requesting dependencies as constructor parameters over resolving services from `RequestServices`. Requesting dependencies as constructor parameters yields classes that are easier to test.

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| presents_related_as_answer |  |  |
| agree with the judge? (fill after opening the key) |  |  |

## S05 (answer check)

**Question** (vi):

> Integration test viết bằng xUnit của mình load file theo đường dẫn tương đối với `Assembly.Location`, nhưng lúc chạy test thì không tìm thấy file. Nguyên nhân là gì và cấu hình thế nào để khắc phục?

**Ground truth**

- Expected answer: Shadow copying runs the tests in a different directory than the output directory; tests that load files relative to Assembly.Location may run into issues, and you might have to disable shadow copying. With xUnit, add an xunit.runner.json file in the test project directory containing "shadowCopy": false.
- P1 (required): Shadow copying runs the tests in a different directory than the output directory; tests that load files relative to Assembly.Location may run into issues, and you might have to disable shadow copying.
- P2 (required): With xUnit, add an xunit.runner.json file in the test project directory containing "shadowCopy": false.
- Acceptable variations: The JSON may be shown as `{ "shadowCopy": false }`.
- MUST-NOT-CLAIM: A .csproj property or command-line switch disables it (not in the corpus).
- Citation criteria: The cited chunk contains the xunit.runner.json instruction (any copy).

**Answer**:

> Nguyên nhân là do tính năng `shadow copying` khiến các bài kiểm tra (test) được thực thi ở một thư mục khác với thư mục đầu ra, điều này gây ra sự cố khi các bài kiểm tra dựa vào việc tải file theo đường dẫn tương đối với `Assembly.Location` [1]. Để khắc phục khi sử dụng xUnit, bạn cần tạo một file `xunit.runner.json` trong thư mục dự án test của mình với cấu hình tắt shadow copying như sau: 
>
> ```
> {
>   "shadowCopy": false
> }
> ``` [1]

**Cited passages** (1):

[1] #17 — Integration tests in ASP.NET Core > Disable shadow copying

> ## Disable shadow copying
>
> Shadow copying causes the tests to execute in a different directory than the output directory. If your tests rely on loading files relative to `Assembly.Location` and you encounter issues, you might have to disable shadow copying.
>
> To disable shadow copying when using xUnit, create a `xunit.runner.json` file in your test project directory, with the [correct configuration setting](https://xunit.net/docs/configuration-files#shadowCopy):
>
> ```
> {
>   "shadowCopy": false
> }
> ```

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| P1 covered |  |  |
| P2 covered |  |  |
| contradicts ground truth |  |  |
| unsupported claims |  |  |
| citation [1] supports its claim |  |  |
| agree with the judge? (fill after opening the key) |  |  |

## S06 (answer check)

**Question** (en):

> Bots keep requesting /robots.txt and /favicon.ico on my ASP.NET Core app, which has neither file, and every one of those requests runs through the whole middleware pipeline, including authentication. How can I cheaply end these requests without running the rest of the pipeline?

**Ground truth**

- Expected answer: Use `app.MapShortCircuit(404, "robots.txt", "favicon.ico");` to short-circuit several URL prefixes at once. Short-circuiting makes routing invoke the endpoint logic immediately and end the request, so middleware that would run after routing (e.g. authentication or CORS) is skipped.
- P1 (required): Use `app.MapShortCircuit(404, "robots.txt", "favicon.ico");` to short-circuit several URL prefixes at once.
- P2 (required): Short-circuiting makes routing invoke the endpoint logic immediately and end the request, so middleware that would run after routing (e.g. authentication or CORS) is skipped.
- P3 (optional, context only): A single route can use `.ShortCircuit()` (optionally with a status code); MapShortCircuit returns IEndpointConventionBuilder, so constraints such as host filtering can be added.
- P4 (optional, context only): Caveat: it doesn't affect middleware placed before UseRouting, and endpoints with [Authorize] or [RequireCors] metadata fail with InvalidOperationException.
- Acceptable variations: The status code may be different if the answer explains it's the response code.
- MUST-NOT-CLAIM: A custom middleware or static files are required.
- Citation criteria: The cited chunk contains MapShortCircuit or the ShortCircuit explanation.

**Answer**:

> You can use the `MapShortCircuit` method to set up short-circuiting for multiple routes at once by passing a params array of URL prefixes [1]. For example, to handle `/robots.txt` and `/favicon.ico` with a status code of `404`, use one line of code [1]: `app.MapShortCircuit(404, "robots.txt", "favicon.ico");` [1]. This causes routing to invoke the endpoint logic immediately and end the request, filtering out known requests early in the pipeline without running the rest of the middleware (such as authentication or CORS) [2].

**Cited passages** (2):

[1] #23 — Routing in ASP.NET Core > Short-circuit middleware after routing

> method can optionally take a status code.
>
> Use the [MapShortCircuit](/en-us/dotnet/api/microsoft.aspnetcore.routing.routeshortcircuitendpointroutebuilderextensions.mapshortcircuit) method to set up short-circuiting for multiple routes at once, by passing to it a params array of URL prefixes. For example, browsers and bots often probe servers for well known paths like `robots.txt` and `favicon.ico`. If the app doesn't have those files, one line of code can configure both routes:
>
> ```
> app.MapShortCircuit(404, "robots.txt", "favicon.ico");
> ```
>
> `MapShortCircuit` returns [IEndpointConventionBuilder](/en-us/dotnet/api/microsoft.aspnetcore.builder.iendpointconventionbuilder) so that additional route constraints like host filtering can be added to it.

[2] #23 — Routing in ASP.NET Core > Short-circuit middleware after routing

> ## Short-circuit middleware after routing
>
> When routing matches an endpoint, it typically lets the rest of the middleware pipeline run before invoking the endpoint logic. Services can reduce resource usage by filtering out known requests early in the pipeline. Use the [ShortCircuit](/en-us/dotnet/api/microsoft.aspnetcore.builder.routeshortcircuitendpointconventionbuilderextensions.shortcircuit) extension method to cause routing to invoke the endpoint logic immediately and then end the request. For example, a given route might not need to go through authentication or CORS middleware. The following example short-circuits requests that match the `/short-circuit` route:
>
> ```
> app.MapGet("/short-circuit", () => "Short circuiting!").ShortCircuit();
> ```
>
> The [ShortCircuit(IEndpointConventionBuilder, Nullable<Int32>)](/en-us/dotnet/api/microsoft.aspnetcore.builder.routeshortcircuitendpointconventionbuilderextensions.shortcircuit#microsoft-aspnetcore-builder-routeshortcircuitendpointconventionbuilderextensions-shortcircuit(microsoft-aspnetcore-builder-iendpointconventionbuilder-system-nullable((system-int32)))) method can optionally take a status code.

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

## S07 (answer check)

**Question** (vi):

> Integration test viết bằng xUnit của mình load file theo đường dẫn tương đối với `Assembly.Location`, nhưng lúc chạy test thì không tìm thấy file. Nguyên nhân là gì và cấu hình thế nào để khắc phục?

**Ground truth**

- Expected answer: Shadow copying runs the tests in a different directory than the output directory; tests that load files relative to Assembly.Location may run into issues, and you might have to disable shadow copying. With xUnit, add an xunit.runner.json file in the test project directory containing "shadowCopy": false.
- P1 (required): Shadow copying runs the tests in a different directory than the output directory; tests that load files relative to Assembly.Location may run into issues, and you might have to disable shadow copying.
- P2 (required): With xUnit, add an xunit.runner.json file in the test project directory containing "shadowCopy": false.
- Acceptable variations: The JSON may be shown as `{ "shadowCopy": false }`.
- MUST-NOT-CLAIM: A .csproj property or command-line switch disables it (not in the corpus).
- Citation criteria: The cited chunk contains the xunit.runner.json instruction (any copy).

**Answer**:

> Nguyên nhân là do tính năng shadow copying khiến các bài test thực thi ở một thư mục khác với thư mục đầu ra, gây ra vấn đề khi các bài test dựa vào việc load file theo đường dẫn tương đối với `Assembly.Location` [1][2][3][4][5]. Để khắc phục khi sử dụng xUnit, bạn cần tạo một file `xunit.runner.json` trong thư mục dự án test của mình với cấu hình sau: ```
> {
>   "shadowCopy": false
> }
> ``` [1][2][3][4][5]

**Cited passages** (5):

[1] #17 — Integration tests in ASP.NET Core > How the test infrastructure infers the app content root path

> tion.Assembly.FullName`. In case an attribute with the correct key isn't found, `WebApplicationFactory` falls back to searching for a solution file (*.sln*) and appends the `TEntryPoint` assembly name to the solution directory. The app root directory (the content root path) is used to discover views and content files.
>
> ## Disable shadow copying
>
> Shadow copying causes the tests to execute in a different directory than the output directory. If your tests rely on loading files relative to `Assembly.Location` and you encounter issues, you might have to disable shadow copying.
>
> To disable shadow copying when using xUnit, create a `xunit.runner.json` file in your test project directory, with the [correct configuration setting](https://xunit.net/docs/configuration-files#shadowCopy):
>
> ```
> {
>   "shadowCopy": false
> }
> ```
>
> ## Disposal of objects
>
> After the tests of the `IClassFixture` implementation are executed, [TestServer](/en-us/dotnet/api/microsoft.aspnetcore.testhost.testserver) and [HttpClient](/en-us/dotnet/api/system.net.http.httpclient) are disposed when xUnit disposes of the [`WebApplicationFactory`](/en-us/dotnet/api/microsoft.aspnetcore.mvc.testing.webapplicationfactory-1). If objects instantiated by the developer require disposal, dispose of them in the `IClassFixture` implementation. For more information, see [Implementing a Dispose method](/en-us/dotnet/standard/garbage-collection/implementing-dispose).
>
> After the tests of the `TestClass` are executed, [TestServer](/en-us/dotnet/api/microsoft.aspnetcore.testhost.testserver) and [HttpClient](/en-us/dotnet/api/system.net.

[2] #17 — Integration tests in ASP.NET Core > How the test infrastructure infers the app content root path

> to the `TEntryPoint` assembly `System.Reflection.Assembly.FullName`. In case an attribute with the correct key isn't found, `WebApplicationFactory` falls back to searching for a solution file (*.sln*) and appends the `TEntryPoint` assembly name to the solution directory. The app root directory (the content root path) is used to discover views and content files.
>
> ## Disable shadow copying
>
> Shadow copying causes the tests to execute in a different directory than the output directory. If your tests rely on loading files relative to `Assembly.Location` and you encounter issues, you might have to disable shadow copying.
>
> To disable shadow copying when using xUnit, create a `xunit.runner.json` file in your test project directory, with the [correct configuration setting](https://xunit.net/docs/configuration-files#shadowCopy):
>
> ```
> {
>   "shadowCopy": false
> }
> ```
>
> ## Disposal of objects
>
> After the tests of the `IClassFixture` implementation are executed, [TestServer](/en-us/dotnet/api/microsoft.aspnetcore.testhost.testserver) and [HttpClient](/en-us/dotnet/api/system.net.http.httpclient) are disposed when xUnit disposes of the [`WebApplicationFactory`](/en-us/dotnet/api/microsoft.aspnetcore.mvc.testing.webapplicationfactory-1). If objects instantiated by the developer require disposal, dispose of them in the `IClassFixture` implementation. For more information, see [Implementing a Dispose method](/en-us/dotnet/standard/garbage-collection/implementing-dispose).
>
> ## Integration tests sample
>
> The [sample app](https://github.com/dotnet/AspNetCore.Docs.Samples/tree/main/test/integration-t

[3] #17 — Integration tests in ASP.NET Core > How the test infrastructure infers the app content root path

> ionFactory` falls back to searching for a solution file (*.sln*) and appends the `TEntryPoint` assembly name to the solution directory. The app root directory (the content root path) is used to discover views and content files.
>
> ## Disable shadow copying
>
> Shadow copying causes the tests to execute in a different directory than the output directory. If your tests rely on loading files relative to `Assembly.Location` and you encounter issues, you might have to disable shadow copying.
>
> To disable shadow copying when using xUnit, create a `xunit.runner.json` file in your test project directory, with the [correct configuration setting](https://xunit.net/docs/configuration-files#shadowCopy):
>
> ```
> {
>   "shadowCopy": false
> }
> ```
>
> ## Disposal of objects
>
> After the tests of the `IClassFixture` implementation are executed, [TestServer](/en-us/dotnet/api/microsoft.aspnetcore.testhost.testserver) and [HttpClient](/en-us/dotnet/api/system.net.http.httpclient) are disposed when xUnit disposes of the [`WebApplicationFactory`](/en-us/dotnet/api/microsoft.aspnetcore.mvc.testing.webapplicationfactory-1). If objects instantiated by the developer require disposal, dispose of them in the `IClassFixture` implementation. For more information, see [Implementing a Dispose method](/en-us/dotnet/standard/garbage-collection/implementing-dispose).
>
> After the tests of the `TestClass` are executed, [TestServer](/en-us/dotnet/api/microsoft.aspnetcore.testhost.testserver) and [HttpClient](/en-us/dotnet/api/system.net.http.httpclient) are disposed when MSTest disposes of the [`WebApplicationFactory`](/en-us/d

[4] #17 — Integration tests in ASP.NET Core > Disable shadow copying

> .Location` and you encounter issues, you might have to disable shadow copying.
>
> To disable shadow copying when using xUnit, create a `xunit.runner.json` file in your test project directory, with the [correct configuration setting](https://xunit.net/docs/configuration-files#shadowCopy):
>
> ```
> {
>   "shadowCopy": false
> }
> ```
>
> ## Disposal of objects
>
> After the tests of the `IClassFixture` implementation are executed, [TestServer](/en-us/dotnet/api/microsoft.aspnetcore.testhost.testserver) and [HttpClient](/en-us/dotnet/api/system.net.http.httpclient) are disposed when xUnit disposes of the [`WebApplicationFactory`](/en-us/dotnet/api/microsoft.aspnetcore.mvc.testing.webapplicationfactory-1). If objects instantiated by the developer require disposal, dispose of them in the `IClassFixture` implementation. For more information, see [Implementing a Dispose method](/en-us/dotnet/standard/garbage-collection/implementing-dispose).
>
> ## Integration tests sample
>
> The [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/test/integration-tests/samples) is composed of two apps:
>
> | App | Project directory | Description |
> | --- | --- | --- |
> | Message app (the SUT) | `src/RazorPagesProject` | Allows a user to add, delete one, delete all, and analyze messages. |
> | Test app | `tests/RazorPagesProject.Tests` | Used to integration test the SUT. |
>
> The tests can be run using the built-in test features of an IDE, such as [Visual Studio](https://visualstudio.microsoft.com). If using [Visual Studio Code](https://code.visualstudio.com/) or the command line, execute the following co

[5] #17 — Integration tests in ASP.NET Core > Set the environment

> prefixed with `ASPNETCORE`.
>
> ```
> protected override IHostBuilder CreateHostBuilder() =>
>     base.CreateHostBuilder()
>         .ConfigureHostConfiguration(
>             config => config.AddEnvironmentVariables("ASPNETCORE"));
> ```
>
> If the SUT uses the Web Host (`IWebHostBuilder`), override `CreateWebHostBuilder`:
>
> ```
> protected override IWebHostBuilder CreateWebHostBuilder() =>
>     base.CreateWebHostBuilder().UseEnvironment("Testing");
> ```
>
> ## How the test infrastructure infers the app content root path
>
> The `WebApplicationFactory` constructor infers the app [content root](../fundamentals/?view=aspnetcore-10.0#content-root) path by searching for a [WebApplicationFactoryContentRootAttribute](/en-us/dotnet/api/microsoft.aspnetcore.mvc.testing.webapplicationfactorycontentrootattribute) on the assembly containing the integration tests with a key equal to the `TEntryPoint` assembly `System.Reflection.Assembly.FullName`. In case an attribute with the correct key isn't found, `WebApplicationFactory` falls back to searching for a solution file (*.sln*) and appends the `TEntryPoint` assembly name to the solution directory. The app root directory (the content root path) is used to discover views and content files.
>
> ## Disable shadow copying
>
> Shadow copying causes the tests to execute in a different directory than the output directory. If your tests rely on loading files relative to `Assembly.Location` and you encounter issues, you might have to disable shadow copying.
>
> To disable shadow copying when using xUnit, create a `xunit.runner.json` file in your test project directory, with the [

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| P1 covered |  |  |
| P2 covered |  |  |
| contradicts ground truth |  |  |
| unsupported claims |  |  |
| citation [1] supports its claim |  |  |
| citation [2] supports its claim |  |  |
| citation [3] supports its claim |  |  |
| citation [4] supports its claim |  |  |
| citation [5] supports its claim |  |  |
| agree with the judge? (fill after opening the key) |  |  |

## S08 (answer check)

**Question** (vi):

> Trong ASP.NET Core, UseStatusCodePagesWithRedirects và UseStatusCodePagesWithReExecute khác nhau thế nào? Cái nào giữ nguyên status code 404 gốc trả về cho client, và cái nào làm URL trên thanh địa chỉ trình duyệt đổi sang trang lỗi?

**Ground truth**

- Expected answer: UseStatusCodePagesWithRedirects sends a 302 Found to the client and redirects it to the error endpoint (which typically returns 200); the original status code is not preserved. UseStatusCodePagesWithReExecute re-executes the request pipeline with an alternate path to generate the response body and does not alter the status code, so the original code is returned. With redirects the browser address bar shows the error endpoint; with re-execute it shows the originally requested URL.
- P1 (required): UseStatusCodePagesWithRedirects sends a 302 Found to the client and redirects it to the error endpoint (which typically returns 200); the original status code is not preserved.
- P2 (required): UseStatusCodePagesWithReExecute re-executes the request pipeline with an alternate path to generate the response body and does not alter the status code, so the original code is returned.
- P3 (required): With redirects the browser address bar shows the error endpoint; with re-execute it shows the originally requested URL.
- P4 (optional, context only): Both take a URL template with a {0} status-code placeholder; the re-execute template must start with '/'.
- P5 (optional, context only): Variants 1-4 add that the re-executed pipeline may change the status code; if it doesn't, the original code is sent.
- Acceptable variations: "HTTP 302" / "Found" / "redirect response"
- MUST-NOT-CLAIM: UseStatusCodePagesWithReExecute redirects the client.; UseStatusCodePagesWithRedirects preserves the original status code.
- Citation criteria: At least one cited chunk for each method; each claim cited from the matching method's section (any variant).

**Answer**:

> Trong ASP.NET Core, hai phương thức này có các điểm khác biệt sau: Phương thức `UseStatusCodePagesWithRedirects` chuyển hướng client đến một endpoint xử lý lỗi được cung cấp trong mẫu URL (thường trả về HTTP 200) và không giữ nguyên mã trạng thái gốc với phản hồi chuyển hướng ban đầu [4][5]. Trong các ứng dụng web, thanh địa chỉ trình duyệt của client phản ánh endpoint được chuyển hướng [3][4][5]. Ngược lại, phương thức `UseStatusCodePagesWithReExecute` tạo phần thân phản hồi bằng cách thực thi lại chuỗi yêu cầu (request pipeline) sử dụng một đường dẫn thay thế, không làm thay đổi mã trạng thái trước hoặc sau khi thực thi lại pipeline, và trả về mã trạng thái gốc cho client [1][2][3]. Trong các ứng dụng web với `UseStatusCodePagesWithReExecute`, thanh địa chỉ trình duyệt của client phản ánh endpoint được yêu cầu ban đầu [1][3]. Do đó, `UseStatusCodePagesWithReExecute` giữ nguyên mã trạng thái gốc trả về cho client [1][2][3], còn `UseStatusCodePagesWithRedirects` làm URL trên thanh địa chỉ trình duyệt đổi sang trang lỗi (endpoint được chuyển hướng) [3][4][5].

**Cited passages** (5):

[4] #13 — Handle errors in ASP.NET Core > UseStatusCodePages > UseStatusCodePagesWithRedirects

> to the error handling endpoint provided in the URL template. The error handling endpoint typically displays error information and returns HTTP 200.
>
> ```
> var app = builder.Build();
>
> if (!app.Environment.IsDevelopment())
> {
>     app.UseExceptionHandler("/Error");
>     app.UseHsts();
> }
>
> app.UseStatusCodePagesWithRedirects("/StatusCode/{0}");
> ```
>
> The URL template can include a `{0}` placeholder for the status code, as shown in the preceding code. If the URL template starts with `~` (tilde), the `~` is replaced by the app's `PathBase`. When specifying an endpoint in the app, create an MVC view or Razor page for the endpoint.
>
> This method is commonly used when the app:
>
> - Should redirect the client to a different endpoint, usually in cases where a different app processes the error. For web apps, the client's browser address bar reflects the redirected endpoint.
> - Shouldn't preserve and return the original status code with the initial redirect response.
>
> ### UseStatusCodePagesWithReExecute
>
> The [UseStatusCodePagesWithReExecute](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithreexecute) extension method:
>
> - Returns the original status code to the client.
> - Generates the response body by re-executing the request pipeline using an alternate path.
>
> ```
> var app = builder.Build();
>
> if (!app.Environment.IsDevelopment())
> {
>     app.UseExceptionHandler("/Error");
>     app.UseHsts();
> }
>
> app.UseStatusCodePagesWithReExecute("/StatusCode/{0}");
> ```
>
> If an endpoint within the app is specified, create an MVC view or Razor page for the endpoint.
>
> This m

[5] #13 — Handle errors in ASP.NET Core > UseStatusCodePages > UseStatusCodePagesWithRedirects

> tus/302) status code to the client.
> - Redirects the client to the error handling endpoint provided in the URL template. The error handling endpoint typically displays error information and returns HTTP 200.
>
> ```
> var app = builder.Build();
>
> if (!app.Environment.IsDevelopment())
> {
>     app.UseExceptionHandler("/Error");
>     app.UseHsts();
> }
>
> app.UseStatusCodePagesWithRedirects("/StatusCode/{0}");
> ```
>
> The URL template can include a `{0}` placeholder for the status code, as shown in the preceding code. If the URL template starts with `~` (tilde), the `~` is replaced by the app's `PathBase`. When specifying an endpoint in the app, create an MVC view or Razor page for the endpoint.
>
> This method is commonly used when the app:
>
> - Should redirect the client to a different endpoint, usually in cases where a different app processes the error. For web apps, the client's browser address bar reflects the redirected endpoint.
> - Shouldn't preserve and return the original status code with the initial redirect response.
>
> ### UseStatusCodePagesWithReExecute
>
> The [UseStatusCodePagesWithReExecute](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithreexecute) extension method:
>
> - Generates the response body by re-executing the request pipeline using an alternate path.
> - Does not alter the status code before or after re-executing the pipeline.
>
> The new pipeline execution may alter the response's status code, as the new pipeline has full control of the status code. If the new pipeline does not alter the status code, the original status code will be sent

[3] #13 — Handle errors in ASP.NET Core > UseStatusCodePages > UseStatusCodePagesWithRedirects

> ), the `~` is replaced by the app's `PathBase`. When specifying an endpoint in the app, create an MVC view or Razor page for the endpoint.
>
> This method is commonly used when the app:
>
> - Should redirect the client to a different endpoint, usually in cases where a different app processes the error. For web apps, the client's browser address bar reflects the redirected endpoint.
> - Shouldn't preserve and return the original status code with the initial redirect response.
>
> ### UseStatusCodePagesWithReExecute
>
> The [UseStatusCodePagesWithReExecute](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithreexecute) extension method:
>
> - Generates the response body by re-executing the request pipeline using an alternate path.
> - Does not alter the status code before or after re-executing the pipeline.
>
> The new pipeline execution may alter the response's status code, as the new pipeline has full control of the status code. If the new pipeline does not alter the status code, the original status code will be sent to the client.
>
> ```
> var app = builder.Build();
>
> if (!app.Environment.IsDevelopment())
> {
>     app.UseExceptionHandler("/Error");
>     app.UseHsts();
> }
>
> app.UseStatusCodePagesWithReExecute("/StatusCode/{0}");
> ```
>
> If an endpoint within the app is specified, create an MVC view or Razor page for the endpoint.
>
> This method is commonly used when the app should:
>
> - Process the request without redirecting to a different endpoint. For web apps, the client's browser address bar reflects the originally requested endpoint.
> - Preserve and return the origi

[1] #13 — Handle errors in ASP.NET Core > UseStatusCodePages > UseStatusCodePagesWithRedirects

> d endpoint.
> - Shouldn't preserve and return the original status code with the initial redirect response.
>
> ### UseStatusCodePagesWithReExecute
>
> The [UseStatusCodePagesWithReExecute](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithreexecute) extension method:
>
> - Generates the response body by re-executing the request pipeline using an alternate path.
> - Does not alter the status code before or after re-executing the pipeline.
>
> The new pipeline execution may alter the response's status code, as the new pipeline has full control of the status code. If the new pipeline does not alter the status code, the original status code will be sent to the client.
>
> ```
> var app = builder.Build();
>
> if (!app.Environment.IsDevelopment())
> {
>     app.UseExceptionHandler("/Error");
>     app.UseHsts();
> }
>
> app.UseStatusCodePagesWithReExecute("/StatusCode/{0}");
> ```
>
> If an endpoint within the app is specified, create an MVC view or Razor page for the endpoint.
>
> This method is commonly used when the app should:
>
> - Process the request without redirecting to a different endpoint. For web apps, the client's browser address bar reflects the originally requested endpoint.
> - Preserve and return the original status code with the response.
>
> The URL template must start with `/` and may include a placeholder `{0}` for the status code. To pass the status code as a query-string parameter, pass a second argument into `UseStatusCodePagesWithReExecute`. For example:
>
> ```
> var app = builder.Build();  
> app.UseStatusCodePagesWithReExecute("/StatusCode", "?statusCode={0}");
> ```

[2] #13 — Handle errors in ASP.NET Core > UseStatusCodePages > UseStatusCodePagesWithRedirects

> rve and return the original status code with the initial redirect response.
>
> To test `UseStatusCodePages` in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x), remove the comments from `webBuilder.UseStartup<StartupSCredirect>();` in `Program.cs`.
>
> ### UseStatusCodePagesWithReExecute
>
> The [UseStatusCodePagesWithReExecute](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithreexecute) extension method:
>
> - Returns the original status code to the client.
> - Generates the response body by re-executing the request pipeline using an alternate path.
>
> ```
> public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
> {
>     if (env.IsDevelopment())
>     {
>         app.UseDeveloperExceptionPage();
>     }
>     else
>     {
>         app.UseExceptionHandler("/Error");
>         app.UseHsts();
>     }
>
>     app.UseStatusCodePagesWithReExecute("/MyStatusCode2", "?code={0}");
>
>     app.UseHttpsRedirection();
>     app.UseStaticFiles();
>
>     app.UseRouting();
>
>     app.UseAuthorization();
>
>     app.UseEndpoints(endpoints =>
>     {
>         endpoints.MapRazorPages();
>     });
> }
> ```
>
> If an endpoint within the app is specified, create an MVC view or Razor page for the endpoint. Ensure `UseStatusCodePagesWithReExecute` is placed before `UseRouting` so the request can be rerouted to the status page. For a Razor Pages example, see [Pages/MyStatusCode2.cshtml](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x/ErrorHandlingSample/Pages) in the [s

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| P1 covered |  |  |
| P2 covered |  |  |
| P3 covered |  |  |
| contradicts ground truth |  |  |
| unsupported claims |  |  |
| citation [4] supports its claim |  |  |
| citation [5] supports its claim |  |  |
| citation [3] supports its claim |  |  |
| citation [1] supports its claim |  |  |
| citation [2] supports its claim |  |  |
| agree with the judge? (fill after opening the key) |  |  |

## S09 (answer check)

**Question** (vi):

> Với `var x = 0xFF_FF_FF_FF;` thì x có kiểu gì và giá trị bao nhiêu? Nếu mình muốn lấy -1 kiểu int từ literal này thì phải viết thế nào?

**Ground truth**

- Expected answer: Without a suffix, the literal's type is the first of int, uint, long, ulong that can represent the value. So `0xFF_FF_FF_FF` is the uint value 4,294,967,295, not int -1: literals are interpreted as positive values. To get -1 as int, cast in an unchecked context: `unchecked((int)0xFF_FF_FF_FF)`.
- P1 (required): Without a suffix, the literal's type is the first of int, uint, long, ulong that can represent the value.
- P2 (required): So `0xFF_FF_FF_FF` is the uint value 4,294,967,295, not int -1: literals are interpreted as positive values.
- P3 (required): To get -1 as int, cast in an unchecked context: `unchecked((int)0xFF_FF_FF_FF)`.
- P4 (optional, context only): U/u suffix: first of uint, ulong; L/l suffix: first of long, ulong.
- Acceptable variations: The value may be written as 4294967295 or 2^32 - 1.
- MUST-NOT-CLAIM: `0xFF_FF_FF_FF` is an int with value -1.; Unsuffixed integer literals are always int.
- Citation criteria: The cited chunk is from #16 and contains the no-suffix rule or the uint example; a #04 chunk = correct topic, wrong evidence.

**Answer**:

> Với `var x = 0xFF_FF_FF_FF;`, trình biên dịch gán cho `x` kiểu `uint` và giá trị đại diện là `4,294,967,295` [1]. Nếu bạn muốn lấy giá trị `-1` kiểu `int` từ literal này, bạn có thể sử dụng toán tử `unchecked` kết hợp ép kiểu như sau: `unchecked((int)0xFF_FF_FF_FF)` [1].

**Cited passages** (1):

[1] #16 — Integral numeric types (C# reference) > Integer literals

> r decimalLiteral = 42;
> var hexLiteral = 0x2A;
> var binaryLiteral = 0b_0010_1010;
> ```
>
> The preceding example also shows the use of `_` as a *digit separator*. You can use the digit separator with all kinds of numeric literals.
>
> The suffix determines the type of an integer literal as follows:
>
> - If the literal has no suffix, the compiler assigns the type as the first of the following types in which its value can be represented: `int`, `uint`, `long`, `ulong`.
>
>   Note
>
>   The compiler interprets literals as positive values. For example, the literal `0xFF_FF_FF_FF` represents the number `4,294,967,295` of the `uint` type, though it has the same bit representation as the number `-1` of the `int` type. If you need a value of a certain type, cast a literal to that type. Use the `unchecked` operator if a literal value can't be represented in the target type. For example, `unchecked((int)0xFF_FF_FF_FF)` produces `-1`.
> - If the literal includes the `U` or `u` suffix, the compiler assigns the type as the first of the following types in which its value can be represented: `uint`, `ulong`.
> - If the literal includes the `L` or `l` suffix, the compiler assigns the type as the first of the following types in which its value can be represented: `long`, `ulong`.
>
>   Note
>
>   You can use the lowercase letter `l` as a suffix. However, `l` generates a compiler warning because the letter `l` can be confused with the digit `1`. Use `L` for clarity.
> - If the literal includes one of the `UL`, `Ul`, `uL`, `ul`, `LU`, `Lu`, `lU`, or `lu` suffixes, the compiler assigns the type as `ulong`.
>
> If the value r

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| P1 covered |  |  |
| P2 covered |  |  |
| P3 covered |  |  |
| contradicts ground truth |  |  |
| unsupported claims |  |  |
| citation [1] supports its claim |  |  |
| agree with the judge? (fill after opening the key) |  |  |

## S10 (answer check)

**Question** (en):

> In ASP.NET Core, what is the difference between how a conventional middleware and a middleware that implements IMiddleware get a scoped DbContext, and what extra setup does the IMiddleware one need in the app?

**Ground truth**

- Expected answer: Conventional middleware receives the scoped service (SampleDbContext in the example) as a parameter of InvokeAsync. Factory-activated middleware implements IMiddleware and receives the scoped service through its constructor, because IMiddleware is activated per client request (connection). The factory-activated middleware is registered as a scoped or transient service in the service container; UseMiddleware sees that the type implements IMiddleware and resolves it with the registered IMiddlewareFactory.
- P1 (required): Conventional middleware receives the scoped service (SampleDbContext in the example) as a parameter of InvokeAsync.
- P2 (required): Factory-activated middleware implements IMiddleware and receives the scoped service through its constructor, because IMiddleware is activated per client request (connection).
- P3 (required): The factory-activated middleware is registered as a scoped or transient service in the service container; UseMiddleware sees that the type implements IMiddleware and resolves it with the registered IMiddlewareFactory.
- P4 (optional, context only): Benefits: activation per client request (injection of scoped services) and strong typing.
- Acceptable variations: "MiddlewareFactory" (the default IMiddlewareFactory) may be named.
- MUST-NOT-CLAIM: Factory-activated middleware is registered as a singleton.; Conventional middleware takes scoped services in its constructor.
- Citation criteria: One citation per slot: S1 from the #11 intro (any variant, including text under 'Additional resources') for P2/P3; S2 from #11 'IMiddleware' (the conventional InvokeAsync signature) or #10 'Service lifetimes' for P1.

**Answer**:

> When using convention-based middleware, scoped services like `SampleDbContext` are injected directly into the `InvokeAsync` method parameters rather than the constructor [2]. In contrast, middleware implementing `IMiddleware` is activated per client request, which allows scoped services to be injected directly into the middleware's constructor (such as `SampleDbContext` in `FactoryActivatedMiddleware`) [1][2][4]. For extra setup, factory-activated middleware needs to be added to the built-in container as a transient service in `Program.cs` (e.g., `builder.Services.AddTransient<FactoryActivatedMiddleware>();`) [3].

**Cited passages** (4):

[2] #11 — Factory-based middleware activation in ASP.NET Core > IMiddleware

> .imiddleware) defines middleware for the app's request pipeline. The [InvokeAsync(HttpContext, RequestDelegate)](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware.invokeasync) method handles requests and returns a [Task](/en-us/dotnet/api/system.threading.tasks.task) that represents the execution of the middleware.
>
> Middleware activated by convention:
>
> ```
> public class ConventionalMiddleware
> {
>     private readonly RequestDelegate _next;
>
>     public ConventionalMiddleware(RequestDelegate next)
>         => _next = next;
>
>     public async Task InvokeAsync(HttpContext context, SampleDbContext dbContext)
>     {
>         var keyValue = context.Request.Query["key"];
>
>         if (!string.IsNullOrWhiteSpace(keyValue))
>         {
>             dbContext.Requests.Add(new Request("Conventional", keyValue));
>
>             await dbContext.SaveChangesAsync();
>         }
>
>         await _next(context);
>     }
> }
> ```
>
> Middleware activated by [MiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.middlewarefactory):
>
> ```
> public class FactoryActivatedMiddleware : IMiddleware
> {
>     private readonly SampleDbContext _dbContext;
>
>     public FactoryActivatedMiddleware(SampleDbContext dbContext)
>         => _dbContext = dbContext;
>
>     public async Task InvokeAsync(HttpContext context, RequestDelegate next)
>     {
>         var keyValue = context.Request.Query["key"];
>
>         if (!string.IsNullOrWhiteSpace(keyValue))
>         {
>             _dbContext.Requests.Add(new Request("Factory", keyValue));
>
>             await _dbContext.SaveChangesAsync();
>         }
>
>         await next(context);
>     }
> }
> ```

[1] #11 — Factory-based middleware activation in ASP.NET Core > Additional resources

> iddleware](/en-us/dotnet/api/microsoft.aspnetcore.builder.usemiddlewareextensions.usemiddleware) extension methods check if a middleware's registered type implements [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware). If it does, the [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) instance registered in the container is used to resolve the [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) implementation instead of using the convention-based middleware activation logic. The middleware is registered as a [scoped or transient service](../dependency-injection?view=aspnetcore-10.0#service-lifetimes) in the app's service container.
>
> Benefits:
>
> - Activation per client request (injection of scoped services)
> - Strong typing of middleware
>
> [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is activated per client request (connection), so scoped services can be injected into the middleware's constructor.
>
> [View or download sample code](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/middleware/extensibility/samples) ([how to download](../?view=aspnetcore-10.0#how-to-download-a-sample))
>
> ## IMiddleware
>
> [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) defines middleware for the app's request pipeline. The [InvokeAsync(HttpContext, RequestDelegate)](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware.invokeasync) method handles requests and returns a [Task](/en-us/dotnet/api/system.threading.tasks.task) that represents the execution of t

[4] #11 — Factory-based middleware activation in ASP.NET Core

> # Factory-based middleware activation in ASP.NET Core
>
> [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory)/[IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is an extensibility point for [middleware](./?view=aspnetcore-10.0) activation that offers the following benefits:
>
> - Activation per client request (injection of scoped services)
> - Strong typing of middleware
>
> [UseMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.builder.usemiddlewareextensions.usemiddleware) extension methods check if a middleware's registered type implements [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware). If it does, the [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) instance registered in the container is used to resolve the [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) implementation instead of using the convention-based middleware activation logic. The middleware is registered as a [scoped or transient service](../dependency-injection?view=aspnetcore-10.0#service-lifetimes) in the app's service container.
>
> [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is activated per client request (connection), so scoped services can be injected into the middleware's constructor.
>
> ## IMiddleware
>
> [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) defines middleware for the app's request pipeline. The [InvokeAsync(HttpContext, RequestDelegate)](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware.invokeasync) method handles req

[3] #11 — Factory-based middleware activation in ASP.NET Core > IMiddleware

> Space(keyValue))
>         {
>             _dbContext.Requests.Add(new Request("Factory", keyValue));
>
>             await _dbContext.SaveChangesAsync();
>         }
>
>         await next(context);
>     }
> }
> ```
>
> Extensions are created for the middleware:
>
> ```
> public static class MiddlewareExtensions
> {
>     public static IApplicationBuilder UseConventionalMiddleware(
>         this IApplicationBuilder app)
>         => app.UseMiddleware<ConventionalMiddleware>();
>
>     public static IApplicationBuilder UseFactoryActivatedMiddleware(
>         this IApplicationBuilder app)
>         => app.UseMiddleware<FactoryActivatedMiddleware>();
> }
> ```
>
> It isn't possible to pass objects to the factory-activated middleware with [UseMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.builder.usemiddlewareextensions.usemiddleware):
>
> ```
> public static IApplicationBuilder UseFactoryActivatedMiddleware(
>     this IApplicationBuilder app, bool option)
> {
>     // Passing 'option' as an argument throws a NotSupportedException at runtime.
>     return app.UseMiddleware<FactoryActivatedMiddleware>(option);
> }
> ```
>
> The factory-activated middleware is added to the built-in container in `Program.cs`:
>
> ```
> var builder = WebApplication.CreateBuilder(args);
>
> builder.Services.AddDbContext<SampleDbContext>
>     (options => options.UseInMemoryDatabase("SampleDb"));
>
> builder.Services.AddTransient<FactoryActivatedMiddleware>();
> ```
>
> Both middleware are registered in the request processing pipeline, also in `Program.cs`:
>
> ```
> var app = builder.Build();
>
> app.UseConventionalMiddleware();
> app.UseFactoryActivatedMiddleware();
> ```
>
> ## IMiddlewa

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| P1 covered |  |  |
| P2 covered |  |  |
| P3 covered |  |  |
| contradicts ground truth |  |  |
| unsupported claims |  |  |
| citation [2] supports its claim |  |  |
| citation [1] supports its claim |  |  |
| citation [4] supports its claim |  |  |
| citation [3] supports its claim |  |  |
| agree with the judge? (fill after opening the key) |  |  |
