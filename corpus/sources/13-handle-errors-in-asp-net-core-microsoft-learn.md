# Handle errors in ASP.NET Core | Microsoft Learn

Source: https://learn.microsoft.com/en-us/aspnet/core/fundamentals/error-handling?view=aspnetcore-10.0

---

---

Note

Access to this page requires authorization. You can try [signing in](#) or changing directories.

Access to this page requires authorization. You can try changing directories.

# Handle errors in ASP.NET Core

Note

This isn't the latest version of this article. For the current release, see the [.NET 10 version of this article](?view=aspnetcore-10.0&preserve-view=true).

Warning

This version of ASP.NET Core is no longer supported. For more information, see the [.NET and .NET Core Support Policy](https://dotnet.microsoft.com/platform/support/policy/dotnet-core). For the current release, see the [.NET 10 version of this article](?view=aspnetcore-10.0&preserve-view=true).

This article covers common approaches to handling errors in ASP.NET Core web apps. See also [Handle errors in ASP.NET Core APIs](error-handling-api?view=aspnetcore-10.0).

For Blazor error handling guidance, which adds to or supersedes the guidance in this article, see [Handle errors in ASP.NET Core Blazor apps](../blazor/fundamentals/handle-errors?view=aspnetcore-10.0).

## Developer exception page

The *Developer Exception Page* displays detailed information about unhandled request exceptions. It uses [DeveloperExceptionPageMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.developerexceptionpagemiddleware) to capture synchronous and asynchronous exceptions from the HTTP pipeline and to generate error responses. The developer exception page runs early in the middleware pipeline, so that it can catch unhandled exceptions thrown in middleware that follows.

ASP.NET Core apps enable the developer exception page by default when both:

- Running in the [`Development` environment](environments?view=aspnetcore-10.0).
- The app was created with the current templates, that is, by using [WebApplication.CreateBuilder](/en-us/dotnet/api/microsoft.aspnetcore.builder.webapplication.createbuilder).

Apps created using earlier templates, that is, by using [WebHost.CreateDefaultBuilder](/en-us/dotnet/api/microsoft.aspnetcore.webhost.createdefaultbuilder), can enable the developer exception page by calling [`app.UseDeveloperExceptionPage`](/en-us/dotnet/api/microsoft.aspnetcore.builder.developerexceptionpageextensions.usedeveloperexceptionpage#microsoft-aspnetcore-builder-developerexceptionpageextensions-usedeveloperexceptionpage(microsoft-aspnetcore-builder-iapplicationbuilder)).

Warning

Don't enable the Developer Exception Page **unless the app is running in the `Development` environment**. Don't share detailed exception information publicly when the app runs in production. For more information on configuring environments, see [ASP.NET Core runtime environments](environments?view=aspnetcore-10.0).

The Developer Exception Page can include the following information about the exception and the request:

- Stack trace
- Query string parameters, if any
- Cookies, if any
- Headers
- Endpoint metadata, if any

The Developer Exception Page isn't guaranteed to provide any information. Use [Logging](logging/?view=aspnetcore-10.0) for complete error information.

The following image shows a sample developer exception page with animation to show the tabs and the information displayed:

![Developer exception page animated to show each tab selected.](error-handling/_static/aspnetcore-developer-page-improvements.gif?view=aspnetcore-10.0)

In response to a request with an `Accept: text/plain` header, the Developer Exception Page returns plain text instead of HTML. For example:

```
Status: 500 Internal Server Error
Time: 9.39 msSize: 480 bytes
FormattedRawHeadersRequest
Body
text/plain; charset=utf-8, 480 bytes
System.InvalidOperationException: Sample Exception
   at WebApplicationMinimal.Program.<>c.<Main>b__0_0() in C:\Source\WebApplicationMinimal\Program.cs:line 12
   at lambda_method1(Closure, Object, HttpContext)
   at Microsoft.AspNetCore.Diagnostics.DeveloperExceptionPageMiddlewareImpl.Invoke(HttpContext context)

HEADERS
=======
Accept: text/plain
Host: localhost:7267
traceparent: 00-0eab195ea19d07b90a46cd7d6bf2f
```

## Exception handler page

To configure a custom error handling page for the [`Production` environment](environments?view=aspnetcore-10.0), call [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). This exception handling middleware:

- Catches and logs unhandled exceptions.
- Re-executes the request in an alternate pipeline using the path indicated. The request isn't re-executed if the response has started. The template-generated code re-executes the request using the `/Error` path.

Warning

If the alternate pipeline throws an exception of its own, exception handling middleware rethrows the original exception.

Since this middleware can re-execute the request pipeline:

- Middlewares need to handle reentrancy with the same request. This normally means either cleaning up their state after calling `_next` or caching their processing on the `HttpContext` to avoid redoing it. When dealing with the request body, this either means buffering or caching the results like the Form reader.
- For the [UseExceptionHandler(IApplicationBuilder, String)](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler#microsoft-aspnetcore-builder-exceptionhandlerextensions-useexceptionhandler(microsoft-aspnetcore-builder-iapplicationbuilder-system-string)) overload that is used in templates, only the request path is modified, and the route data is cleared. Request data such as headers, method, and items are all reused as-is.
- Scoped services remain the same.

In the following example, [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler) adds the exception handling middleware in non-`Development` environments:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}
```

The Razor Pages app template provides an Error page (`.cshtml`) and [PageModel](/en-us/dotnet/api/microsoft.aspnetcore.mvc.razorpages.pagemodel) class (`ErrorModel`) in the *Pages* folder. For an MVC app, the project template includes an `Error` action method and an Error view for the Home controller.

The exception handling middleware re-executes the request using the *original* HTTP method. If an error handler endpoint is restricted to a specific set of HTTP methods, it runs only for those HTTP methods. For example, an MVC controller action that uses the `[HttpGet]` attribute runs only for GET requests. To ensure that *all* requests reach the custom error handling page, don't restrict them to a specific set of HTTP methods.

To handle exceptions differently based on the original HTTP method:

- For Razor Pages, create multiple handler methods. For example, use `OnGet` to handle GET exceptions and use `OnPost` to handle POST exceptions.
- For MVC, apply HTTP verb attributes to multiple actions. For example, use `[HttpGet]` to handle GET exceptions and use `[HttpPost]` to handle POST exceptions.

To allow unauthenticated users to view the custom error handling page, ensure that it supports anonymous access.

### Access the exception

Use [IExceptionHandlerPathFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandlerpathfeature) to access the exception and the original request path in an error handler. The following example uses `IExceptionHandlerPathFeature` to get more information about the exception that was thrown:

```
[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
[IgnoreAntiforgeryToken]
public class ErrorModel : PageModel
{
    public string? RequestId { get; set; }

    public bool ShowRequestId => !string.IsNullOrEmpty(RequestId);

    public string? ExceptionMessage { get; set; }

    public void OnGet()
    {
        RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;

        var exceptionHandlerPathFeature =
            HttpContext.Features.Get<IExceptionHandlerPathFeature>();

        if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
        {
            ExceptionMessage = "The file was not found.";
        }

        if (exceptionHandlerPathFeature?.Path == "/")
        {
            ExceptionMessage ??= string.Empty;
            ExceptionMessage += " Page: Home.";
        }
    }
}
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

## Exception handler lambda

An alternative to a [custom exception handler page](#exception-handler-page) is to provide a lambda to [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). Using a lambda allows access to the error before returning the response.

The following code uses a lambda for exception handling:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler(exceptionHandlerApp =>
    {
        exceptionHandlerApp.Run(async context =>
        {
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;

            // using static System.Net.Mime.MediaTypeNames;
            context.Response.ContentType = Text.Plain;

            await context.Response.WriteAsync("An exception was thrown.");

            var exceptionHandlerPathFeature =
                context.Features.Get<IExceptionHandlerPathFeature>();

            if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
            {
                await context.Response.WriteAsync(" The file was not found.");
            }

            if (exceptionHandlerPathFeature?.Path == "/")
            {
                await context.Response.WriteAsync(" Page: Home.");
            }
        });
    });

    app.UseHsts();
}
```

Another way to use a lambda is to set the status code based on the exception type, as in the following example:

```
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddProblemDetails();
var app = builder.Build();
if (app.Environment.IsDevelopment())
{
    app.UseExceptionHandler(new ExceptionHandlerOptions
    {
        StatusCodeSelector = ex => ex is TimeoutException
            ? StatusCodes.Status503ServiceUnavailable
            : StatusCodes.Status500InternalServerError
    });
}
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

## IExceptionHandler

[IExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandler) is an interface that gives the developer a callback for handling known exceptions in a central location. The interface contains a single method, [`TryHandleAsync`](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandler.tryhandleasync), which receives an `HttpContext` and an `Exception` parameter.

`IExceptionHandler` implementations are registered by calling [`IServiceCollection.AddExceptionHandler<T>`](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.exceptionhandlerservicecollectionextensions.addexceptionhandler). The lifetime of an `IExceptionHandler` instance is singleton. Multiple implementations can be added, and they're called in the order registered.

Important

Registering an `IExceptionHandler` implementation isn't sufficient on its own. Registered handlers are invoked by the exception handling middleware, so the app must also add that middleware by calling [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). If `UseExceptionHandler` isn't called, the registered `IExceptionHandler` implementations are never called.

Exception handling middleware iterates through registered exception handlers in order until one returns `true` from `TryHandleAsync`, indicating that the exception has been handled. If an exception handler handles an exception, it can return `true` to stop processing. If an exception isn't handled by any exception handler, then control falls back to the default behavior and options from the middleware.

Starting in .NET 10, the default behavior is to suppress emission of diagnostics such as logs and metrics for handled exceptions (when `TryHandleAsync` returns `true`). This differs from earlier versions (.NET 8 and 9) where diagnostics were always emitted regardless of whether the exception was handled. The default behavior can be changed by setting [SuppressDiagnosticsCallback](#suppressdiagnosticscallback).

The following example shows an `IExceptionHandler` implementation:

```
using Microsoft.AspNetCore.Diagnostics;

namespace ErrorHandlingSample
{
    public class CustomExceptionHandler : IExceptionHandler
    {
        private readonly ILogger<CustomExceptionHandler> logger;
        public CustomExceptionHandler(ILogger<CustomExceptionHandler> logger)
        {
            this.logger = logger;
        }
        public ValueTask<bool> TryHandleAsync(
            HttpContext httpContext,
            Exception exception,
            CancellationToken cancellationToken)
        {
            var exceptionMessage = exception.Message;
            logger.LogError(
                "Error Message: {exceptionMessage}, Time of occurrence {time}",
                exceptionMessage, DateTime.UtcNow);
            // Return false to continue with the default behavior
            // - or - return true to signal that this exception is handled
            return ValueTask.FromResult(false);
        }
    }
}
```

The following example shows how to register an `IExceptionHandler` implementation for dependency injection and add the exception handling middleware that calls it:

```
using ErrorHandlingSample;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDatabaseDeveloperPageExceptionFilter();
builder.Services.AddRazorPages();
builder.Services.AddExceptionHandler<CustomExceptionHandler>();

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

// Remaining Program.cs code omitted for brevity
```

### Configure `UseExceptionHandler` when using `IExceptionHandler`

The exception handling middleware requires a fallback for exceptions that no `IExceptionHandler` handles. If none is configured, calling `app.UseExceptionHandler()` with no arguments throws the following exception at startup:

`System.InvalidOperationException: An error occurred when configuring the exception handler middleware. Either the 'ExceptionHandlingPath' or the 'ExceptionHandler' property must be set in 'UseExceptionHandler()'.`

Use any one of the following to satisfy the requirement:

- Specify an error path: `app.UseExceptionHandler("/Error");`
- Enable problem details: call `builder.Services.AddProblemDetails();` and then `app.UseExceptionHandler();`
- Supply a fallback handler: `app.UseExceptionHandler(exceptionHandlerApp => { ... });`

The `IExceptionHandler` implementations still run first in all of these cases. The configured path, problem details response, or fallback handler is used only when every `TryHandleAsync` returns `false`.

If an `IExceptionHandler` returns `true` without writing a response or setting a status code, the response ends up as `404 Not Found` and the middleware logs:

`The exception handler configured on ExceptionHandlerOptions produced a 404 status response.`

An `IExceptionHandler` that returns `true` should write the complete response, including the status code. For example, set `httpContext.Response.StatusCode` and write the body, or call `IProblemDetailsService.TryWriteAsync`. If a 404 response is intentional, set [AllowStatusCode404Response](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandleroptions.allowstatuscode404response#microsoft-aspnetcore-builder-exceptionhandleroptions-allowstatuscode404response) to `true`.

When the preceding code runs in the `Development` environment:

- The `CustomExceptionHandler` is called first to handle an exception.
- After logging the exception, the `TryHandleAsync` method returns `false`, so the [developer exception page](#developer-exception-page) is shown.

In other environments:

- The `CustomExceptionHandler` is called first to handle an exception.
- After logging the exception, the `TryHandleAsync` method returns `false`, so the [`/Error` page](#exception-handler-page) is shown.

If `TryHandleAsync` returns `true` instead:

- The remaining `IExceptionHandler` implementations aren't called.
- The exception handler page, path, or lambda configured on `UseExceptionHandler` isn't used. The handler is responsible for writing the entire response.

### SuppressDiagnosticsCallback

Starting in .NET 10, you can control whether the exception handling middleware writes diagnostics for handled exceptions by configuring the `SuppressDiagnosticsCallback` property on `ExceptionHandlerOptions`. This callback receives the exception context and allows you to determine whether diagnostics should be suppressed based on the specific exception or request.

To revert to the .NET 8 and 9 behavior where diagnostics are always emitted for handled exceptions, set the callback to always return `false`:

```
app.UseExceptionHandler(new ExceptionHandlerOptions
{
    SuppressDiagnosticsCallback = context => false
});
```

You can also conditionally suppress diagnostics based on the exception type or other context:

```
app.UseExceptionHandler(new ExceptionHandlerOptions
{
    SuppressDiagnosticsCallback = context => context.Exception is ArgumentException
});
```

When an exception isn't handled by any `IExceptionHandler` implementation (all handlers return `false` from `TryHandleAsync`), control falls back to the default behavior and options from the middleware, and diagnostics are emitted according to the middleware's standard behavior.

## UseStatusCodePages

By default, an ASP.NET Core app doesn't provide a status code page for HTTP error status codes, such as *404 - Not Found*. When the app sets an HTTP 400-599 error status code that doesn't have a body, it returns the status code and an empty response body. To enable default text-only handlers for common error status codes, call [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) in `Program.cs`:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePages();
```

Call `UseStatusCodePages` before request handling middleware. For example, call `UseStatusCodePages` before the static file middleware and the endpoints middleware.

When `UseStatusCodePages` isn't used, navigating to a URL without an endpoint returns a browser-dependent error message indicating the endpoint can't be found. When `UseStatusCodePages` is called, the browser returns the following response:

```
Status Code: 404; Not Found
```

`UseStatusCodePages` isn't typically used in production because it returns a message that isn't useful to users.

Note

The status code pages middleware does **not** catch exceptions. To provide a custom error handling page, use the [exception handler page](#exception-handler-page).

### UseStatusCodePages with format string

To customize the response content type and text, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a content type and format string:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

// using static System.Net.Mime.MediaTypeNames;
app.UseStatusCodePages(Text.Plain, "Status Code Page: {0}");
```

In the preceding code, `{0}` is a placeholder for the error code.

`UseStatusCodePages` with a format string isn't typically used in production because it returns a message that isn't useful to users.

### UseStatusCodePages with lambda

To specify custom error-handling and response-writing code, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a lambda expression:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePages(async statusCodeContext =>
{
    // using static System.Net.Mime.MediaTypeNames;
    statusCodeContext.HttpContext.Response.ContentType = Text.Plain;

    await statusCodeContext.HttpContext.Response.WriteAsync(
        $"Status Code Page: {statusCodeContext.HttpContext.Response.StatusCode}");
});
```

`UseStatusCodePages` with a lambda isn't typically used in production because it returns a message that isn't useful to users.

### UseStatusCodePagesWithRedirects

The [UseStatusCodePagesWithRedirects](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithredirects) extension method:

- Sends a [302 - Found](https://developer.mozilla.org/docs/Web/HTTP/Status/302) status code to the client.
- Redirects the client to the error handling endpoint provided in the URL template. The error handling endpoint typically displays error information and returns HTTP 200.

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePagesWithRedirects("/StatusCode/{0}");
```

The URL template can include a `{0}` placeholder for the status code, as shown in the preceding code. If the URL template starts with `~` (tilde), the `~` is replaced by the app's `PathBase`. When specifying an endpoint in the app, create an MVC view or Razor page for the endpoint.

This method is commonly used when the app:

- Should redirect the client to a different endpoint, usually in cases where a different app processes the error. For web apps, the client's browser address bar reflects the redirected endpoint.
- Shouldn't preserve and return the original status code with the initial redirect response.

### UseStatusCodePagesWithReExecute

The [UseStatusCodePagesWithReExecute](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithreexecute) extension method:

- Generates the response body by re-executing the request pipeline using an alternate path.
- Does not alter the status code before or after re-executing the pipeline.

The new pipeline execution may alter the response's status code, as the new pipeline has full control of the status code. If the new pipeline does not alter the status code, the original status code will be sent to the client.

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePagesWithReExecute("/StatusCode/{0}");
```

If an endpoint within the app is specified, create an MVC view or Razor page for the endpoint.

This method is commonly used when the app should:

- Process the request without redirecting to a different endpoint. For web apps, the client's browser address bar reflects the originally requested endpoint.
- Preserve and return the original status code with the response.

The URL template must start with `/` and may include a placeholder `{0}` for the status code. To pass the status code as a query-string parameter, pass a second argument into `UseStatusCodePagesWithReExecute`. For example:

```
var app = builder.Build();  
app.UseStatusCodePagesWithReExecute("/StatusCode", "?statusCode={0}");
```

The endpoint that processes the error can get the original URL that generated the error, as shown in the following example:

```
[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
public class StatusCodeModel : PageModel
{
    public int OriginalStatusCode { get; set; }

    public string? OriginalPathAndQuery { get; set; }

    public void OnGet(int statusCode)
    {
        OriginalStatusCode = statusCode;

        var statusCodeReExecuteFeature =
            HttpContext.Features.Get<IStatusCodeReExecuteFeature>();

        if (statusCodeReExecuteFeature is not null)
        {
            OriginalPathAndQuery = $"{statusCodeReExecuteFeature.OriginalPathBase}"
                                    + $"{statusCodeReExecuteFeature.OriginalPath}"
                                    + $"{statusCodeReExecuteFeature.OriginalQueryString}";

        }
    }
}
```

Since this middleware can re-execute the request pipeline:

- Middlewares need to handle reentrancy with the same request. This normally means either cleaning up their state after calling `_next` or caching their processing on the `HttpContext` to avoid redoing it. When dealing with the request body, this either means buffering or caching the results like the Form reader.
- Scoped services remain the same.

## Disable status code pages

To disable status code pages for an MVC controller or action method, use the [[SkipStatusCodePages]](/en-us/dotnet/api/microsoft.aspnetcore.mvc.skipstatuscodepagesattribute) attribute.

To disable status code pages for specific requests in a Razor Pages handler method or in an MVC controller, use [IStatusCodePagesFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.istatuscodepagesfeature):

```
public void OnGet()
{
    var statusCodePagesFeature =
        HttpContext.Features.Get<IStatusCodePagesFeature>();

    if (statusCodePagesFeature is not null)
    {
        statusCodePagesFeature.Enabled = false;
    }
}
```

## Exception-handling code

Code in exception handling pages can also throw exceptions. Production error pages should be tested thoroughly and take extra care to avoid throwing exceptions of their own.

### Response headers

Once the headers for a response are sent:

- The app can't change the response's status code.
- Any exception pages or handlers can't run. The response must be completed or the connection aborted.

## Server exception handling

In addition to the exception handling logic in an app, the [HTTP server implementation](servers/?view=aspnetcore-10.0) can handle some exceptions. If the server catches an exception before response headers are sent, the server sends a `500 - Internal Server Error` response without a response body. If the server catches an exception after response headers are sent, the server closes the connection. Requests that aren't handled by the app are handled by the server. Any exception that occurs when the server is handling the request is handled by the server's exception handling. The app's custom error pages, exception handling middleware, and filters don't affect this behavior.

## Startup exception handling

Only the hosting layer can handle exceptions that take place during app startup. The host can be configured to [capture startup errors](host/web-host?view=aspnetcore-10.0#capture-startup-errors) and [capture detailed errors](host/web-host?view=aspnetcore-10.0#detailed-errors).

The hosting layer can show an error page for a captured startup error only if the error occurs after host address/port binding. If binding fails:

- The hosting layer logs a critical exception.
- The dotnet process crashes.
- No error page is displayed when the HTTP server is [Kestrel](servers/kestrel?view=aspnetcore-10.0).

When running on [IIS](/en-us/iis) (or Azure App Service) or [IIS Express](/en-us/iis/extensions/introduction-to-iis-express/iis-express-overview), a *502.5 - Process Failure* is returned by the [ASP.NET Core Module](../host-and-deploy/aspnet-core-module?view=aspnetcore-10.0) if the process can't start. For more information, see [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0).

## Database error page

The Database developer page exception filter [AddDatabaseDeveloperPageExceptionFilter](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.databasedeveloperpageexceptionfilterserviceextensions.adddatabasedeveloperpageexceptionfilter) captures database-related exceptions that can be resolved by using Entity Framework Core migrations. When these exceptions occur, an HTML response is generated with details of possible actions to resolve the issue. This page is enabled only in the `Development` environment. The following code adds the Database developer page exception filter:

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDatabaseDeveloperPageExceptionFilter();
builder.Services.AddRazorPages();
```

## Exception filters

In MVC apps, exception filters can be configured globally or on a per-controller or per-action basis. In Razor Pages apps, they can be configured globally or per page model. These filters handle any unhandled exceptions that occur during the execution of a controller action or another filter. For more information, see [Filters in ASP.NET Core](../mvc/controllers/filters?view=aspnetcore-10.0#exception-filters).

Exception filters are useful for trapping exceptions that occur within MVC actions, but they're not as flexible as the built-in [exception handling middleware](https://github.com/dotnet/aspnetcore/blob/main/src/Middleware/Diagnostics/src/ExceptionHandler/ExceptionHandlerMiddleware.cs), [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). We recommend using `UseExceptionHandler`, unless you need to perform error handling differently based on which MVC action is chosen.

## Model state errors

For information about how to handle model state errors, see [Model binding](../mvc/models/model-binding?view=aspnetcore-10.0) and [Model validation](../mvc/models/validation?view=aspnetcore-10.0).

## Problem details

[Problem Details](https://www.rfc-editor.org/rfc/rfc7807.html) are not the only response format to describe an HTTP API error, however, they are commonly used to report errors for HTTP APIs.

The problem details service implements the [IProblemDetailsService](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice) interface, which supports creating problem details in ASP.NET Core. The [AddProblemDetails(IServiceCollection)](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.problemdetailsservicecollectionextensions.addproblemdetails#microsoft-extensions-dependencyinjection-problemdetailsservicecollectionextensions-addproblemdetails(microsoft-extensions-dependencyinjection-iservicecollection)) extension method on [IServiceCollection](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.iservicecollection) registers the default `IProblemDetailsService` implementation.

In ASP.NET Core apps, the following middleware generates problem details HTTP responses when `AddProblemDetails` is called, except when the [`Accept` request HTTP header](https://developer.mozilla.org/docs/Web/HTTP/Headers/Accept) doesn't include one of the content types supported by the registered [IProblemDetailsWriter](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailswriter) (default: `application/json`):

- [ExceptionHandlerMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.exceptionhandlermiddleware): Generates a problem details response when a custom handler is not defined.
- [StatusCodePagesMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.statuscodepagesmiddleware): Generates a problem details response by default.
- [DeveloperExceptionPageMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.developerexceptionpagemiddleware): Generates a problem details response in development when the `Accept` request HTTP header doesn't include `text/html`.

The following code configures the app to generate a problem details response for all HTTP client and server error responses that ***don't have body content yet***:

```
builder.Services.AddProblemDetails();

var app = builder.Build();        

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler();
    app.UseHsts();
}

app.UseStatusCodePages();
```

The next section shows how to customize the problem details response body.

### Customize problem details

The automatic creation of a `ProblemDetails` can be customized using any of the following options:

1. Use [`ProblemDetailsOptions.CustomizeProblemDetails`](#customizeproblemdetails-operation)
2. Use a custom [`IProblemDetailsWriter`](#custom-iproblemdetailswriter)
3. Call the [`IProblemDetailsService` in a middleware](#problem-details-from-middleware)

#### `CustomizeProblemDetails` operation

The generated problem details can be customized using [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails), and the customizations are applied to all auto-generated problem details.

The following code uses [ProblemDetailsOptions](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions) to set [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails):

```
builder.Services.AddProblemDetails(options =>
    options.CustomizeProblemDetails = ctx =>
            ctx.ProblemDetails.Extensions.Add("nodeId", Environment.MachineName));

var app = builder.Build();        

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler();
    app.UseHsts();
}

app.UseStatusCodePages();
```

For example, an [`HTTP Status 400 Bad Request`](https://developer.mozilla.org/docs/Web/HTTP/Status/400) endpoint result produces the following problem details response body:

```
{
  "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
  "title": "Bad Request",
  "status": 400,
  "nodeId": "my-machine-name"
}
```

#### Custom `IProblemDetailsWriter`

An [IProblemDetailsWriter](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailswriter) implementation can be created for advanced customizations.

```
public class SampleProblemDetailsWriter : IProblemDetailsWriter
{
    // Indicates that only responses with StatusCode == 400
    // are handled by this writer. All others are
    // handled by different registered writers if available.
    public bool CanWrite(ProblemDetailsContext context)
        => context.HttpContext.Response.StatusCode == 400;

    public ValueTask WriteAsync(ProblemDetailsContext context)
    {
        // Additional customizations.

        // Write to the response.
        var response = context.HttpContext.Response;
        return new ValueTask(response.WriteAsJsonAsync(context.ProblemDetails));
    }
}
```

***Note:*** When using a custom `IProblemDetailsWriter`, the custom `IProblemDetailsWriter` must be registered before calling [AddRazorPages](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addrazorpages), [AddControllers](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addcontrollers), [AddControllersWithViews](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addcontrollerswithviews), or [AddMvc](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addmvc):

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddTransient<IProblemDetailsWriter, SampleProblemDetailsWriter>();

var app = builder.Build();

// Middleware to handle writing problem details to the response.
app.Use(async (context, next) =>
{
    await next(context);
    var mathErrorFeature = context.Features.Get<MathErrorFeature>();
    if (mathErrorFeature is not null)
    {
        if (context.RequestServices.GetService<IProblemDetailsWriter>() is
            { } problemDetailsService)
        {

            if (problemDetailsService.CanWrite(new ProblemDetailsContext() { HttpContext = context }))
            {
                (string Detail, string Type) details = mathErrorFeature.MathError switch
                {
                    MathErrorType.DivisionByZeroError => ("Divison by zero is not defined.",
                        "https://en.wikipedia.org/wiki/Division_by_zero"),
                    _ => ("Negative or complex numbers are not valid input.",
                        "https://en.wikipedia.org/wiki/Square_root")
                };

                await problemDetailsService.WriteAsync(new ProblemDetailsContext
                {
                    HttpContext = context,
                    ProblemDetails =
                    {
                        Title = "Bad Input",
                        Detail = details.Detail,
                        Type = details.Type
                    }
                });
            }
        }
    }
});

// /divide?numerator=2&denominator=4
app.MapGet("/divide", (HttpContext context, double numerator, double denominator) =>
{
    if (denominator == 0)
    {
        var errorType = new MathErrorFeature
        {
            MathError = MathErrorType.DivisionByZeroError
        };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(numerator / denominator);
});

// /squareroot?radicand=16
app.MapGet("/squareroot", (HttpContext context, double radicand) =>
{
    if (radicand < 0)
    {
        var errorType = new MathErrorFeature
        {
            MathError = MathErrorType.NegativeRadicandError
        };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(Math.Sqrt(radicand));
});

app.Run();
```

#### Problem details from middleware

An alternative approach to using [ProblemDetailsOptions](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions) with [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails) is to set the [ProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailscontext.problemdetails#microsoft-aspnetcore-http-problemdetailscontext-problemdetails) in middleware. A problem details response can be written by calling [`IProblemDetailsService.WriteAsync`](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice.writeasync?view=aspnetcore-7.0&preserve-view=true):

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseHttpsRedirection();
app.UseStatusCodePages();

// Middleware to handle writing problem details to the response.
app.Use(async (context, next) =>
{
    await next(context);
    var mathErrorFeature = context.Features.Get<MathErrorFeature>();
    if (mathErrorFeature is not null)
    {
        if (context.RequestServices.GetService<IProblemDetailsService>() is
                                                           { } problemDetailsService)
        {
            (string Detail, string Type) details = mathErrorFeature.MathError switch
            {
                MathErrorType.DivisionByZeroError => ("Divison by zero is not defined.",
                "https://en.wikipedia.org/wiki/Division_by_zero"),
                _ => ("Negative or complex numbers are not valid input.", 
                "https://en.wikipedia.org/wiki/Square_root")
            };

            await problemDetailsService.WriteAsync(new ProblemDetailsContext
            {
                HttpContext = context,
                ProblemDetails =
                {
                    Title = "Bad Input",
                    Detail = details.Detail,
                    Type = details.Type
                }
            });
        }
    }
});

// /divide?numerator=2&denominator=4
app.MapGet("/divide", (HttpContext context, double numerator, double denominator) =>
{
    if (denominator == 0)
    {
        var errorType = new MathErrorFeature { MathError =
                                               MathErrorType.DivisionByZeroError };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(numerator / denominator);
});

// /squareroot?radicand=16
app.MapGet("/squareroot", (HttpContext context, double radicand) =>
{
    if (radicand < 0)
    {
        var errorType = new MathErrorFeature { MathError =
                                               MathErrorType.NegativeRadicandError };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(Math.Sqrt(radicand));
});

app.MapControllers();

app.Run();
```

In the preceding code, the Minimal API endpoints `/divide` and `/squareroot` return the expected custom problem response on error input.

The API controller endpoints return the default problem response on error input, not the custom problem response. The default problem response is returned because the API controller has written to the response stream, [Problem details for error status codes](/en-us/aspnet/core/web-api/#problem-details-for-error-status-codes), before [`IProblemDetailsService.WriteAsync`](https://github.com/dotnet/aspnetcore/blob/ce2db7ea0b161fc5eb35710fca6feeafeeac37bc/src/Http/Http.Extensions/src/ProblemDetailsService.cs#L24) is called and the response is **not** written again.

The following `ValuesController` returns [BadRequestResult](/en-us/dotnet/api/microsoft.aspnetcore.mvc.badrequestresult), which writes to the response stream and therefore prevents the custom problem response from being returned.

```
[Route("api/[controller]/[action]")]
[ApiController]
public class ValuesController : ControllerBase
{
    // /api/values/divide/1/2
    [HttpGet("{Numerator}/{Denominator}")]
    public IActionResult Divide(double Numerator, double Denominator)
    {
        if (Denominator == 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.DivisionByZeroError
            };
            HttpContext.Features.Set(errorType);
            return BadRequest();
        }

        return Ok(Numerator / Denominator);
    }

    // /api/values/squareroot/4
    [HttpGet("{radicand}")]
    public IActionResult Squareroot(double radicand)
    {
        if (radicand < 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.NegativeRadicandError
            };
            HttpContext.Features.Set(errorType);
            return BadRequest();
        }

        return Ok(Math.Sqrt(radicand));
    }

}
```

The following `Values3Controller` returns [`ControllerBase.Problem`](/en-us/dotnet/api/microsoft.aspnetcore.mvc.controllerbase.problem) so the expected custom problem result is returned:

```
[Route("api/[controller]/[action]")]
[ApiController]
public class Values3Controller : ControllerBase
{
    // /api/values3/divide/1/2
    [HttpGet("{Numerator}/{Denominator}")]
    public IActionResult Divide(double Numerator, double Denominator)
    {
        if (Denominator == 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.DivisionByZeroError
            };
            HttpContext.Features.Set(errorType);
            return Problem(
                title: "Bad Input",
                detail: "Divison by zero is not defined.",
                type: "https://en.wikipedia.org/wiki/Division_by_zero",
                statusCode: StatusCodes.Status400BadRequest
                );
        }

        return Ok(Numerator / Denominator);
    }

    // /api/values3/squareroot/4
    [HttpGet("{radicand}")]
    public IActionResult Squareroot(double radicand)
    {
        if (radicand < 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.NegativeRadicandError
            };
            HttpContext.Features.Set(errorType);
            return Problem(
                title: "Bad Input",
                detail: "Negative or complex numbers are not valid input.",
                type: "https://en.wikipedia.org/wiki/Square_root",
                statusCode: StatusCodes.Status400BadRequest
                );
        }

        return Ok(Math.Sqrt(radicand));
    }

}
```

## Produce a ProblemDetails payload for exceptions

Consider the following app:

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}

app.MapControllers();
app.Run();
```

In non-development environments, when an exception occurs, the following is a standard [ProblemDetails response](https://datatracker.ietf.org/doc/html/rfc7807) that is returned to the client:

```
{
"type":"https://tools.ietf.org/html/rfc7231#section-6.6.1",
"title":"An error occurred while processing your request.",
"status":500,"traceId":"00-b644<snip>-00"
}
```

For most apps, the preceding code is all that's needed for exceptions. However, the following section shows how to get more detailed problem responses.

An alternative to a [custom exception handler page](error-handling?view=aspnetcore-10.0#exception-handler-page) is to provide a lambda to [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). Using a lambda allows access to the error and writing a problem details response with [`IProblemDetailsService.WriteAsync`](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice.writeasync?view=aspnetcore-7.0&preserve-view=true):

```
using Microsoft.AspNetCore.Diagnostics;
using static System.Net.Mime.MediaTypeNames;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}
else
{
    app.UseExceptionHandler(exceptionHandlerApp =>
    {
        exceptionHandlerApp.Run(async context =>
        {
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;
            context.Response.ContentType = Text.Plain;

            var title = "Bad Input";
            var detail = "Invalid input";
            var type = "https://errors.example.com/badInput";

            if (context.RequestServices.GetService<IProblemDetailsService>() is
                { } problemDetailsService)
            {
                var exceptionHandlerFeature =
               context.Features.Get<IExceptionHandlerFeature>();

                var exceptionType = exceptionHandlerFeature?.Error;
                if (exceptionType != null &&
                   exceptionType.Message.Contains("infinity"))
                {
                    title = "Argument exception";
                    detail = "Invalid input";
                    type = "https://errors.example.com/argumentException";
                }

                await problemDetailsService.WriteAsync(new ProblemDetailsContext
                {
                    HttpContext = context,
                    ProblemDetails =
                {
                    Title = title,
                    Detail = detail,
                    Type = type
                }
                });
            }
        });
    });
}

app.MapControllers();
app.Run();
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

An alternative approach to generate problem details is to use the third-party NuGet package [Hellang.Middleware.ProblemDetails](https://www.nuget.org/packages/Hellang.Middleware.ProblemDetails/) that can be used to map exceptions and client errors to problem details.

## Additional resources

- [View or download sample code](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples) ([how to download](./?view=aspnetcore-10.0#how-to-download-a-sample))
- [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0)
- [Common error troubleshooting for Azure App Service and IIS with ASP.NET Core](../host-and-deploy/azure-iis-errors-reference?view=aspnetcore-10.0)
- [Handle errors in ASP.NET Core APIs](error-handling-api?view=aspnetcore-10.0)
- [Breaking change: Exception diagnostics are suppressed when `IExceptionHandler.TryHandleAsync` returns true](https://github.com/aspnet/Announcements/issues/524)

This article covers common approaches to handling errors in ASP.NET Core web apps. See also [Handle errors in ASP.NET Core APIs](error-handling-api?view=aspnetcore-10.0).

For Blazor error handling guidance, which adds to or supersedes the guidance in this article, see [Handle errors in ASP.NET Core Blazor apps](../blazor/fundamentals/handle-errors?view=aspnetcore-10.0).

## Developer exception page

The *Developer Exception Page* displays detailed information about unhandled request exceptions. It uses [DeveloperExceptionPageMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.developerexceptionpagemiddleware) to capture synchronous and asynchronous exceptions from the HTTP pipeline and to generate error responses. The developer exception page runs early in the middleware pipeline, so that it can catch unhandled exceptions thrown in middleware that follows.

ASP.NET Core apps enable the developer exception page by default when both:

- Running in the [`Development` environment](environments?view=aspnetcore-10.0).
- The app was created with the current templates, that is, by using [WebApplication.CreateBuilder](/en-us/dotnet/api/microsoft.aspnetcore.builder.webapplication.createbuilder).

Apps created using earlier templates, that is, by using [WebHost.CreateDefaultBuilder](/en-us/dotnet/api/microsoft.aspnetcore.webhost.createdefaultbuilder), can enable the developer exception page by calling [`app.UseDeveloperExceptionPage`](/en-us/dotnet/api/microsoft.aspnetcore.builder.developerexceptionpageextensions.usedeveloperexceptionpage#microsoft-aspnetcore-builder-developerexceptionpageextensions-usedeveloperexceptionpage(microsoft-aspnetcore-builder-iapplicationbuilder)).

Warning

Don't enable the Developer Exception Page **unless the app is running in the `Development` environment**. Don't share detailed exception information publicly when the app runs in production. For more information on configuring environments, see [ASP.NET Core runtime environments](environments?view=aspnetcore-10.0).

The Developer Exception Page can include the following information about the exception and the request:

- Stack trace
- Query string parameters, if any
- Cookies, if any
- Headers
- Endpoint metadata, if any

The Developer Exception Page isn't guaranteed to provide any information. Use [Logging](logging/?view=aspnetcore-10.0) for complete error information.

The following image shows a sample developer exception page with animation to show the tabs and the information displayed:

![Developer exception page animated to show each tab selected.](error-handling/_static/aspnetcore-developer-page-improvements.gif?view=aspnetcore-10.0)

In response to a request with an `Accept: text/plain` header, the Developer Exception Page returns plain text instead of HTML. For example:

```
Status: 500 Internal Server Error
Time: 9.39 msSize: 480 bytes
FormattedRawHeadersRequest
Body
text/plain; charset=utf-8, 480 bytes
System.InvalidOperationException: Sample Exception
   at WebApplicationMinimal.Program.<>c.<Main>b__0_0() in C:\Source\WebApplicationMinimal\Program.cs:line 12
   at lambda_method1(Closure, Object, HttpContext)
   at Microsoft.AspNetCore.Diagnostics.DeveloperExceptionPageMiddlewareImpl.Invoke(HttpContext context)

HEADERS
=======
Accept: text/plain
Host: localhost:7267
traceparent: 00-0eab195ea19d07b90a46cd7d6bf2f
```

## Exception handler page

To configure a custom error handling page for the [`Production` environment](environments?view=aspnetcore-10.0), call [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). This exception handling middleware:

- Catches and logs unhandled exceptions.
- Re-executes the request in an alternate pipeline using the path indicated. The request isn't re-executed if the response has started. The template-generated code re-executes the request using the `/Error` path.

Warning

If the alternate pipeline throws an exception of its own, exception handling middleware rethrows the original exception.

Since this middleware can re-execute the request pipeline:

- Middlewares need to handle reentrancy with the same request. This normally means either cleaning up their state after calling `_next` or caching their processing on the `HttpContext` to avoid redoing it. When dealing with the request body, this either means buffering or caching the results like the Form reader.
- For the [UseExceptionHandler(IApplicationBuilder, String)](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler#microsoft-aspnetcore-builder-exceptionhandlerextensions-useexceptionhandler(microsoft-aspnetcore-builder-iapplicationbuilder-system-string)) overload that is used in templates, only the request path is modified, and the route data is cleared. Request data such as headers, method, and items are all reused as-is.
- Scoped services remain the same.

In the following example, [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler) adds the exception handling middleware in non-`Development` environments:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}
```

The Razor Pages app template provides an Error page (`.cshtml`) and [PageModel](/en-us/dotnet/api/microsoft.aspnetcore.mvc.razorpages.pagemodel) class (`ErrorModel`) in the *Pages* folder. For an MVC app, the project template includes an `Error` action method and an Error view for the Home controller.

The exception handling middleware re-executes the request using the *original* HTTP method. If an error handler endpoint is restricted to a specific set of HTTP methods, it runs only for those HTTP methods. For example, an MVC controller action that uses the `[HttpGet]` attribute runs only for GET requests. To ensure that *all* requests reach the custom error handling page, don't restrict them to a specific set of HTTP methods.

To handle exceptions differently based on the original HTTP method:

- For Razor Pages, create multiple handler methods. For example, use `OnGet` to handle GET exceptions and use `OnPost` to handle POST exceptions.
- For MVC, apply HTTP verb attributes to multiple actions. For example, use `[HttpGet]` to handle GET exceptions and use `[HttpPost]` to handle POST exceptions.

To allow unauthenticated users to view the custom error handling page, ensure that it supports anonymous access.

### Access the exception

Use [IExceptionHandlerPathFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandlerpathfeature) to access the exception and the original request path in an error handler. The following example uses `IExceptionHandlerPathFeature` to get more information about the exception that was thrown:

```
[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
[IgnoreAntiforgeryToken]
public class ErrorModel : PageModel
{
    public string? RequestId { get; set; }

    public bool ShowRequestId => !string.IsNullOrEmpty(RequestId);

    public string? ExceptionMessage { get; set; }

    public void OnGet()
    {
        RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;

        var exceptionHandlerPathFeature =
            HttpContext.Features.Get<IExceptionHandlerPathFeature>();

        if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
        {
            ExceptionMessage = "The file was not found.";
        }

        if (exceptionHandlerPathFeature?.Path == "/")
        {
            ExceptionMessage ??= string.Empty;
            ExceptionMessage += " Page: Home.";
        }
    }
}
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

## Exception handler lambda

An alternative to a [custom exception handler page](#exception-handler-page) is to provide a lambda to [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). Using a lambda allows access to the error before returning the response.

The following code uses a lambda for exception handling:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler(exceptionHandlerApp =>
    {
        exceptionHandlerApp.Run(async context =>
        {
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;

            // using static System.Net.Mime.MediaTypeNames;
            context.Response.ContentType = Text.Plain;

            await context.Response.WriteAsync("An exception was thrown.");

            var exceptionHandlerPathFeature =
                context.Features.Get<IExceptionHandlerPathFeature>();

            if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
            {
                await context.Response.WriteAsync(" The file was not found.");
            }

            if (exceptionHandlerPathFeature?.Path == "/")
            {
                await context.Response.WriteAsync(" Page: Home.");
            }
        });
    });

    app.UseHsts();
}
```

Another way to use a lambda is to set the status code based on the exception type, as in the following example:

```
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddProblemDetails();
var app = builder.Build();
if (app.Environment.IsDevelopment())
{
    app.UseExceptionHandler(new ExceptionHandlerOptions
    {
        StatusCodeSelector = ex => ex is TimeoutException
            ? StatusCodes.Status503ServiceUnavailable
            : StatusCodes.Status500InternalServerError
    });
}
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

## IExceptionHandler

[IExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandler) is an interface that gives the developer a callback for handling known exceptions in a central location.

`IExceptionHandler` implementations are registered by calling [`IServiceCollection.AddExceptionHandler<T>`](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.exceptionhandlerservicecollectionextensions.addexceptionhandler). The lifetime of an `IExceptionHandler` instance is singleton. Multiple implementations can be added, and they're called in the order registered.

Important

Registering an `IExceptionHandler` implementation isn't sufficient on its own. Registered handlers are invoked by the exception handling middleware, so the app must also add that middleware by calling [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). If `UseExceptionHandler` isn't called, the registered `IExceptionHandler` implementations are never called.

Exception handling middleware iterates through registered exception handlers in order until one returns `true` from `TryHandleAsync`, indicating that the exception has been handled. If an exception handler handles an exception, it can return `true` to stop processing. If an exception isn't handled by any exception handler, then control falls back to the default behavior and options from the middleware.

Note

In .NET 8 and .NET 9, the exception handling middleware logs the exception and emits metrics even when an `IExceptionHandler` implementation returns `true` from `TryHandleAsync`. If the handler does its own logging, the exception is recorded twice: once under the `Microsoft.AspNetCore.Diagnostics.ExceptionHandlerMiddleware` category and once under the handler's category. To log it only from the handler, filter out the middleware category in configuration:

```
{
  "Logging": {
    "LogLevel": {
      "Microsoft.AspNetCore.Diagnostics.ExceptionHandlerMiddleware": "None"
    }
  }
}
```

Starting in .NET 10, diagnostics are suppressed by default for handled exceptions. See [SuppressDiagnosticsCallback](error-handling?view=aspnetcore-10.0#suppressdiagnosticscallback).

The following example shows an `IExceptionHandler` implementation:

```
using Microsoft.AspNetCore.Diagnostics;

namespace ErrorHandlingSample
{
    public class CustomExceptionHandler : IExceptionHandler
    {
        private readonly ILogger<CustomExceptionHandler> logger;
        public CustomExceptionHandler(ILogger<CustomExceptionHandler> logger)
        {
            this.logger = logger;
        }
        public ValueTask<bool> TryHandleAsync(
            HttpContext httpContext,
            Exception exception,
            CancellationToken cancellationToken)
        {
            var exceptionMessage = exception.Message;
            logger.LogError(
                "Error Message: {exceptionMessage}, Time of occurrence {time}",
                exceptionMessage, DateTime.UtcNow);
            // Return false to continue with the default behavior
            // - or - return true to signal that this exception is handled
            return ValueTask.FromResult(false);
        }
    }
}
```

The following example shows how to register an `IExceptionHandler` implementation for dependency injection and add the exception handling middleware that calls it:

```
using ErrorHandlingSample;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDatabaseDeveloperPageExceptionFilter();
builder.Services.AddRazorPages();
builder.Services.AddExceptionHandler<CustomExceptionHandler>();

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

// Remaining Program.cs code omitted for brevity
```

### Configure `UseExceptionHandler` when using `IExceptionHandler`

The exception handling middleware requires a fallback for exceptions that no `IExceptionHandler` handles. If none is configured, calling `app.UseExceptionHandler()` with no arguments throws at startup:

`System.InvalidOperationException: An error occurred when configuring the exception handler middleware. Either the 'ExceptionHandlingPath' or the 'ExceptionHandler' property must be set in 'UseExceptionHandler()'.`

Use any one of the following to satisfy the requirement:

- Specify an error path: `app.UseExceptionHandler("/Error");`
- Enable problem details: call `builder.Services.AddProblemDetails();` and then `app.UseExceptionHandler();`
- Supply a fallback handler: `app.UseExceptionHandler(exceptionHandlerApp => { ... });`

The `IExceptionHandler` implementations still run first in all of these cases. The configured path, problem details response, or fallback handler is used only when every `TryHandleAsync` returns `false`.

If an `IExceptionHandler` returns `true` without writing a response or setting a status code, the response ends up as `404 Not Found` and the middleware logs:

`The exception handler configured on ExceptionHandlerOptions produced a 404 status response.`

An `IExceptionHandler` that returns `true` should write the complete response, including the status code. For example, set `httpContext.Response.StatusCode` and write the body, or call `IProblemDetailsService.TryWriteAsync`. If a 404 response is intentional, set [AllowStatusCode404Response](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandleroptions.allowstatuscode404response#microsoft-aspnetcore-builder-exceptionhandleroptions-allowstatuscode404response) to `true`.

When the preceding code runs in the `Development` environment:

- The `CustomExceptionHandler` is called first to handle an exception.
- After logging the exception, the `TryHandleAsync` method returns `false`, so the [developer exception page](#developer-exception-page) is shown.

In other environments:

- The `CustomExceptionHandler` is called first to handle an exception.
- After logging the exception, the `TryHandleAsync` method returns `false`, so the [`/Error` page](#exception-handler-page) is shown.

If `TryHandleAsync` returns `true` instead:

- The remaining `IExceptionHandler` implementations aren't called.
- The exception handler page, path, or lambda configured on `UseExceptionHandler` isn't used. The handler is responsible for writing the entire response.

## UseStatusCodePages

By default, an ASP.NET Core app doesn't provide a status code page for HTTP error status codes, such as *404 - Not Found*. When the app sets an HTTP 400-599 error status code that doesn't have a body, it returns the status code and an empty response body. To enable default text-only handlers for common error status codes, call [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) in `Program.cs`:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePages();
```

Call `UseStatusCodePages` before request handling middleware. For example, call `UseStatusCodePages` before the static file middleware and the endpoints middleware.

When `UseStatusCodePages` isn't used, navigating to a URL without an endpoint returns a browser-dependent error message indicating the endpoint can't be found. When `UseStatusCodePages` is called, the browser returns the following response:

```
Status Code: 404; Not Found
```

`UseStatusCodePages` isn't typically used in production because it returns a message that isn't useful to users.

Note

The status code pages middleware does **not** catch exceptions. To provide a custom error handling page, use the [exception handler page](#exception-handler-page).

### UseStatusCodePages with format string

To customize the response content type and text, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a content type and format string:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

// using static System.Net.Mime.MediaTypeNames;
app.UseStatusCodePages(Text.Plain, "Status Code Page: {0}");
```

In the preceding code, `{0}` is a placeholder for the error code.

`UseStatusCodePages` with a format string isn't typically used in production because it returns a message that isn't useful to users.

### UseStatusCodePages with lambda

To specify custom error-handling and response-writing code, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a lambda expression:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePages(async statusCodeContext =>
{
    // using static System.Net.Mime.MediaTypeNames;
    statusCodeContext.HttpContext.Response.ContentType = Text.Plain;

    await statusCodeContext.HttpContext.Response.WriteAsync(
        $"Status Code Page: {statusCodeContext.HttpContext.Response.StatusCode}");
});
```

`UseStatusCodePages` with a lambda isn't typically used in production because it returns a message that isn't useful to users.

### UseStatusCodePagesWithRedirects

The [UseStatusCodePagesWithRedirects](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithredirects) extension method:

- Sends a [302 - Found](https://developer.mozilla.org/docs/Web/HTTP/Status/302) status code to the client.
- Redirects the client to the error handling endpoint provided in the URL template. The error handling endpoint typically displays error information and returns HTTP 200.

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePagesWithRedirects("/StatusCode/{0}");
```

The URL template can include a `{0}` placeholder for the status code, as shown in the preceding code. If the URL template starts with `~` (tilde), the `~` is replaced by the app's `PathBase`. When specifying an endpoint in the app, create an MVC view or Razor page for the endpoint.

This method is commonly used when the app:

- Should redirect the client to a different endpoint, usually in cases where a different app processes the error. For web apps, the client's browser address bar reflects the redirected endpoint.
- Shouldn't preserve and return the original status code with the initial redirect response.

### UseStatusCodePagesWithReExecute

The [UseStatusCodePagesWithReExecute](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithreexecute) extension method:

- Generates the response body by re-executing the request pipeline using an alternate path.
- Does not alter the status code before or after re-executing the pipeline.

The new pipeline execution may alter the response's status code, as the new pipeline has full control of the status code. If the new pipeline does not alter the status code, the original status code will be sent to the client.

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePagesWithReExecute("/StatusCode/{0}");
```

If an endpoint within the app is specified, create an MVC view or Razor page for the endpoint.

This method is commonly used when the app should:

- Process the request without redirecting to a different endpoint. For web apps, the client's browser address bar reflects the originally requested endpoint.
- Preserve and return the original status code with the response.

The URL template must start with `/` and may include a placeholder `{0}` for the status code. To pass the status code as a query-string parameter, pass a second argument into `UseStatusCodePagesWithReExecute`. For example:

```
var app = builder.Build();  
app.UseStatusCodePagesWithReExecute("/StatusCode", "?statusCode={0}");
```

The endpoint that processes the error can get the original URL that generated the error, as shown in the following example:

```
[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
public class StatusCodeModel : PageModel
{
    public int OriginalStatusCode { get; set; }

    public string? OriginalPathAndQuery { get; set; }

    public void OnGet(int statusCode)
    {
        OriginalStatusCode = statusCode;

        var statusCodeReExecuteFeature =
            HttpContext.Features.Get<IStatusCodeReExecuteFeature>();

        if (statusCodeReExecuteFeature is not null)
        {
            OriginalPathAndQuery = $"{statusCodeReExecuteFeature.OriginalPathBase}"
                                    + $"{statusCodeReExecuteFeature.OriginalPath}"
                                    + $"{statusCodeReExecuteFeature.OriginalQueryString}";

        }
    }
}
```

Since this middleware can re-execute the request pipeline:

- Middlewares need to handle reentrancy with the same request. This normally means either cleaning up their state after calling `_next` or caching their processing on the `HttpContext` to avoid redoing it. When dealing with the request body, this either means buffering or caching the results like the Form reader.
- Scoped services remain the same.

## Disable status code pages

To disable status code pages for an MVC controller or action method, use the [[SkipStatusCodePages]](/en-us/dotnet/api/microsoft.aspnetcore.mvc.skipstatuscodepagesattribute) attribute.

To disable status code pages for specific requests in a Razor Pages handler method or in an MVC controller, use [IStatusCodePagesFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.istatuscodepagesfeature):

```
public void OnGet()
{
    var statusCodePagesFeature =
        HttpContext.Features.Get<IStatusCodePagesFeature>();

    if (statusCodePagesFeature is not null)
    {
        statusCodePagesFeature.Enabled = false;
    }
}
```

## Exception-handling code

Code in exception handling pages can also throw exceptions. Production error pages should be tested thoroughly and take extra care to avoid throwing exceptions of their own.

### Response headers

Once the headers for a response are sent:

- The app can't change the response's status code.
- Any exception pages or handlers can't run. The response must be completed or the connection aborted.

## Server exception handling

In addition to the exception handling logic in an app, the [HTTP server implementation](servers/?view=aspnetcore-10.0) can handle some exceptions. If the server catches an exception before response headers are sent, the server sends a `500 - Internal Server Error` response without a response body. If the server catches an exception after response headers are sent, the server closes the connection. Requests that aren't handled by the app are handled by the server. Any exception that occurs when the server is handling the request is handled by the server's exception handling. The app's custom error pages, exception handling middleware, and filters don't affect this behavior.

## Startup exception handling

Only the hosting layer can handle exceptions that take place during app startup. The host can be configured to [capture startup errors](host/web-host?view=aspnetcore-10.0#capture-startup-errors) and [capture detailed errors](host/web-host?view=aspnetcore-10.0#detailed-errors).

The hosting layer can show an error page for a captured startup error only if the error occurs after host address/port binding. If binding fails:

- The hosting layer logs a critical exception.
- The dotnet process crashes.
- No error page is displayed when the HTTP server is [Kestrel](servers/kestrel?view=aspnetcore-10.0).

When running on [IIS](/en-us/iis) (or Azure App Service) or [IIS Express](/en-us/iis/extensions/introduction-to-iis-express/iis-express-overview), a *502.5 - Process Failure* is returned by the [ASP.NET Core Module](../host-and-deploy/aspnet-core-module?view=aspnetcore-10.0) if the process can't start. For more information, see [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0).

## Database error page

The Database developer page exception filter [AddDatabaseDeveloperPageExceptionFilter](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.databasedeveloperpageexceptionfilterserviceextensions.adddatabasedeveloperpageexceptionfilter) captures database-related exceptions that can be resolved by using Entity Framework Core migrations. When these exceptions occur, an HTML response is generated with details of possible actions to resolve the issue. This page is enabled only in the `Development` environment. The following code adds the Database developer page exception filter:

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDatabaseDeveloperPageExceptionFilter();
builder.Services.AddRazorPages();
```

## Exception filters

In MVC apps, exception filters can be configured globally or on a per-controller or per-action basis. In Razor Pages apps, they can be configured globally or per page model. These filters handle any unhandled exceptions that occur during the execution of a controller action or another filter. For more information, see [Filters in ASP.NET Core](../mvc/controllers/filters?view=aspnetcore-10.0#exception-filters).

Exception filters are useful for trapping exceptions that occur within MVC actions, but they're not as flexible as the built-in [exception handling middleware](https://github.com/dotnet/aspnetcore/blob/main/src/Middleware/Diagnostics/src/ExceptionHandler/ExceptionHandlerMiddleware.cs), [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). We recommend using `UseExceptionHandler`, unless you need to perform error handling differently based on which MVC action is chosen.

## Model state errors

For information about how to handle model state errors, see [Model binding](../mvc/models/model-binding?view=aspnetcore-10.0) and [Model validation](../mvc/models/validation?view=aspnetcore-10.0).

## Problem details

[Problem Details](https://www.rfc-editor.org/rfc/rfc7807.html) are not the only response format to describe an HTTP API error, however, they are commonly used to report errors for HTTP APIs.

The problem details service implements the [IProblemDetailsService](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice) interface, which supports creating problem details in ASP.NET Core. The [AddProblemDetails(IServiceCollection)](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.problemdetailsservicecollectionextensions.addproblemdetails#microsoft-extensions-dependencyinjection-problemdetailsservicecollectionextensions-addproblemdetails(microsoft-extensions-dependencyinjection-iservicecollection)) extension method on [IServiceCollection](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.iservicecollection) registers the default `IProblemDetailsService` implementation.

In ASP.NET Core apps, the following middleware generates problem details HTTP responses when `AddProblemDetails` is called, except when the [`Accept` request HTTP header](https://developer.mozilla.org/docs/Web/HTTP/Headers/Accept) doesn't include one of the content types supported by the registered [IProblemDetailsWriter](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailswriter) (default: `application/json`):

- [ExceptionHandlerMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.exceptionhandlermiddleware): Generates a problem details response when a custom handler is not defined.
- [StatusCodePagesMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.statuscodepagesmiddleware): Generates a problem details response by default.
- [DeveloperExceptionPageMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.developerexceptionpagemiddleware): Generates a problem details response in development when the `Accept` request HTTP header doesn't include `text/html`.

The following code configures the app to generate a problem details response for all HTTP client and server error responses that ***don't have body content yet***:

```
builder.Services.AddProblemDetails();

var app = builder.Build();        

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler();
    app.UseHsts();
}

app.UseStatusCodePages();
```

The next section shows how to customize the problem details response body.

### Customize problem details

The automatic creation of a `ProblemDetails` can be customized using any of the following options:

1. Use [`ProblemDetailsOptions.CustomizeProblemDetails`](#customizeproblemdetails-operation)
2. Use a custom [`IProblemDetailsWriter`](#custom-iproblemdetailswriter)
3. Call the [`IProblemDetailsService` in a middleware](#problem-details-from-middleware)

#### `CustomizeProblemDetails` operation

The generated problem details can be customized using [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails), and the customizations are applied to all auto-generated problem details.

The following code uses [ProblemDetailsOptions](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions) to set [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails):

```
builder.Services.AddProblemDetails(options =>
    options.CustomizeProblemDetails = ctx =>
            ctx.ProblemDetails.Extensions.Add("nodeId", Environment.MachineName));

var app = builder.Build();        

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler();
    app.UseHsts();
}

app.UseStatusCodePages();
```

For example, an [`HTTP Status 400 Bad Request`](https://developer.mozilla.org/docs/Web/HTTP/Status/400) endpoint result produces the following problem details response body:

```
{
  "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
  "title": "Bad Request",
  "status": 400,
  "nodeId": "my-machine-name"
}
```

#### Custom `IProblemDetailsWriter`

An [IProblemDetailsWriter](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailswriter) implementation can be created for advanced customizations.

```
public class SampleProblemDetailsWriter : IProblemDetailsWriter
{
    // Indicates that only responses with StatusCode == 400
    // are handled by this writer. All others are
    // handled by different registered writers if available.
    public bool CanWrite(ProblemDetailsContext context)
        => context.HttpContext.Response.StatusCode == 400;

    public ValueTask WriteAsync(ProblemDetailsContext context)
    {
        // Additional customizations.

        // Write to the response.
        var response = context.HttpContext.Response;
        return new ValueTask(response.WriteAsJsonAsync(context.ProblemDetails));
    }
}
```

***Note:*** When using a custom `IProblemDetailsWriter`, the custom `IProblemDetailsWriter` must be registered before calling [AddRazorPages](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addrazorpages), [AddControllers](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addcontrollers), [AddControllersWithViews](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addcontrollerswithviews), or [AddMvc](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addmvc):

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddTransient<IProblemDetailsWriter, SampleProblemDetailsWriter>();

var app = builder.Build();

// Middleware to handle writing problem details to the response.
app.Use(async (context, next) =>
{
    await next(context);
    var mathErrorFeature = context.Features.Get<MathErrorFeature>();
    if (mathErrorFeature is not null)
    {
        if (context.RequestServices.GetService<IProblemDetailsWriter>() is
            { } problemDetailsService)
        {

            if (problemDetailsService.CanWrite(new ProblemDetailsContext() { HttpContext = context }))
            {
                (string Detail, string Type) details = mathErrorFeature.MathError switch
                {
                    MathErrorType.DivisionByZeroError => ("Divison by zero is not defined.",
                        "https://en.wikipedia.org/wiki/Division_by_zero"),
                    _ => ("Negative or complex numbers are not valid input.",
                        "https://en.wikipedia.org/wiki/Square_root")
                };

                await problemDetailsService.WriteAsync(new ProblemDetailsContext
                {
                    HttpContext = context,
                    ProblemDetails =
                    {
                        Title = "Bad Input",
                        Detail = details.Detail,
                        Type = details.Type
                    }
                });
            }
        }
    }
});

// /divide?numerator=2&denominator=4
app.MapGet("/divide", (HttpContext context, double numerator, double denominator) =>
{
    if (denominator == 0)
    {
        var errorType = new MathErrorFeature
        {
            MathError = MathErrorType.DivisionByZeroError
        };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(numerator / denominator);
});

// /squareroot?radicand=16
app.MapGet("/squareroot", (HttpContext context, double radicand) =>
{
    if (radicand < 0)
    {
        var errorType = new MathErrorFeature
        {
            MathError = MathErrorType.NegativeRadicandError
        };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(Math.Sqrt(radicand));
});

app.Run();
```

#### Problem details from Middleware

An alternative approach to using [ProblemDetailsOptions](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions) with [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails) is to set the [ProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailscontext.problemdetails#microsoft-aspnetcore-http-problemdetailscontext-problemdetails) in middleware. A problem details response can be written by calling [`IProblemDetailsService.WriteAsync`](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice.writeasync?view=aspnetcore-7.0&preserve-view=true):

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseHttpsRedirection();
app.UseStatusCodePages();

// Middleware to handle writing problem details to the response.
app.Use(async (context, next) =>
{
    await next(context);
    var mathErrorFeature = context.Features.Get<MathErrorFeature>();
    if (mathErrorFeature is not null)
    {
        if (context.RequestServices.GetService<IProblemDetailsService>() is
                                                           { } problemDetailsService)
        {
            (string Detail, string Type) details = mathErrorFeature.MathError switch
            {
                MathErrorType.DivisionByZeroError => ("Divison by zero is not defined.",
                "https://en.wikipedia.org/wiki/Division_by_zero"),
                _ => ("Negative or complex numbers are not valid input.", 
                "https://en.wikipedia.org/wiki/Square_root")
            };

            await problemDetailsService.WriteAsync(new ProblemDetailsContext
            {
                HttpContext = context,
                ProblemDetails =
                {
                    Title = "Bad Input",
                    Detail = details.Detail,
                    Type = details.Type
                }
            });
        }
    }
});

// /divide?numerator=2&denominator=4
app.MapGet("/divide", (HttpContext context, double numerator, double denominator) =>
{
    if (denominator == 0)
    {
        var errorType = new MathErrorFeature { MathError =
                                               MathErrorType.DivisionByZeroError };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(numerator / denominator);
});

// /squareroot?radicand=16
app.MapGet("/squareroot", (HttpContext context, double radicand) =>
{
    if (radicand < 0)
    {
        var errorType = new MathErrorFeature { MathError =
                                               MathErrorType.NegativeRadicandError };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(Math.Sqrt(radicand));
});

app.MapControllers();

app.Run();
```

In the preceding code, the Minimal API endpoints `/divide` and `/squareroot` return the expected custom problem response on error input.

The API controller endpoints return the default problem response on error input, not the custom problem response. The default problem response is returned because the API controller has written to the response stream, [Problem details for error status codes](/en-us/aspnet/core/web-api/#problem-details-for-error-status-codes), before [`IProblemDetailsService.WriteAsync`](https://github.com/dotnet/aspnetcore/blob/ce2db7ea0b161fc5eb35710fca6feeafeeac37bc/src/Http/Http.Extensions/src/ProblemDetailsService.cs#L24) is called and the response is **not** written again.

The following `ValuesController` returns [BadRequestResult](/en-us/dotnet/api/microsoft.aspnetcore.mvc.badrequestresult), which writes to the response stream and therefore prevents the custom problem response from being returned.

```
[Route("api/[controller]/[action]")]
[ApiController]
public class ValuesController : ControllerBase
{
    // /api/values/divide/1/2
    [HttpGet("{Numerator}/{Denominator}")]
    public IActionResult Divide(double Numerator, double Denominator)
    {
        if (Denominator == 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.DivisionByZeroError
            };
            HttpContext.Features.Set(errorType);
            return BadRequest();
        }

        return Ok(Numerator / Denominator);
    }

    // /api/values/squareroot/4
    [HttpGet("{radicand}")]
    public IActionResult Squareroot(double radicand)
    {
        if (radicand < 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.NegativeRadicandError
            };
            HttpContext.Features.Set(errorType);
            return BadRequest();
        }

        return Ok(Math.Sqrt(radicand));
    }

}
```

The following `Values3Controller` returns [`ControllerBase.Problem`](/en-us/dotnet/api/microsoft.aspnetcore.mvc.controllerbase.problem) so the expected custom problem result is returned:

```
[Route("api/[controller]/[action]")]
[ApiController]
public class Values3Controller : ControllerBase
{
    // /api/values3/divide/1/2
    [HttpGet("{Numerator}/{Denominator}")]
    public IActionResult Divide(double Numerator, double Denominator)
    {
        if (Denominator == 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.DivisionByZeroError
            };
            HttpContext.Features.Set(errorType);
            return Problem(
                title: "Bad Input",
                detail: "Divison by zero is not defined.",
                type: "https://en.wikipedia.org/wiki/Division_by_zero",
                statusCode: StatusCodes.Status400BadRequest
                );
        }

        return Ok(Numerator / Denominator);
    }

    // /api/values3/squareroot/4
    [HttpGet("{radicand}")]
    public IActionResult Squareroot(double radicand)
    {
        if (radicand < 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.NegativeRadicandError
            };
            HttpContext.Features.Set(errorType);
            return Problem(
                title: "Bad Input",
                detail: "Negative or complex numbers are not valid input.",
                type: "https://en.wikipedia.org/wiki/Square_root",
                statusCode: StatusCodes.Status400BadRequest
                );
        }

        return Ok(Math.Sqrt(radicand));
    }

}
```

## Produce a ProblemDetails payload for exceptions

Consider the following app:

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}

app.MapControllers();
app.Run();
```

In non-development environments, when an exception occurs, the following is a standard [ProblemDetails response](https://datatracker.ietf.org/doc/html/rfc7807) that is returned to the client:

```
{
"type":"https://tools.ietf.org/html/rfc7231#section-6.6.1",
"title":"An error occurred while processing your request.",
"status":500,"traceId":"00-b644<snip>-00"
}
```

For most apps, the preceding code is all that's needed for exceptions. However, the following section shows how to get more detailed problem responses.

An alternative to a [custom exception handler page](error-handling?view=aspnetcore-10.0#exception-handler-page) is to provide a lambda to [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). Using a lambda allows access to the error and writing a problem details response with [`IProblemDetailsService.WriteAsync`](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice.writeasync?view=aspnetcore-7.0&preserve-view=true):

```
using Microsoft.AspNetCore.Diagnostics;
using static System.Net.Mime.MediaTypeNames;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}
else
{
    app.UseExceptionHandler(exceptionHandlerApp =>
    {
        exceptionHandlerApp.Run(async context =>
        {
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;
            context.Response.ContentType = Text.Plain;

            var title = "Bad Input";
            var detail = "Invalid input";
            var type = "https://errors.example.com/badInput";

            if (context.RequestServices.GetService<IProblemDetailsService>() is
                { } problemDetailsService)
            {
                var exceptionHandlerFeature =
               context.Features.Get<IExceptionHandlerFeature>();

                var exceptionType = exceptionHandlerFeature?.Error;
                if (exceptionType != null &&
                   exceptionType.Message.Contains("infinity"))
                {
                    title = "Argument exception";
                    detail = "Invalid input";
                    type = "https://errors.example.com/argumentException";
                }

                await problemDetailsService.WriteAsync(new ProblemDetailsContext
                {
                    HttpContext = context,
                    ProblemDetails =
                {
                    Title = title,
                    Detail = detail,
                    Type = type
                }
                });
            }
        });
    });
}

app.MapControllers();
app.Run();
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

An alternative approach to generate problem details is to use the third-party NuGet package [Hellang.Middleware.ProblemDetails](https://www.nuget.org/packages/Hellang.Middleware.ProblemDetails/) that can be used to map exceptions and client errors to problem details.

## Additional resources

- [View or download sample code](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples) ([how to download](./?view=aspnetcore-10.0#how-to-download-a-sample))
- [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0)
- [Common error troubleshooting for Azure App Service and IIS with ASP.NET Core](../host-and-deploy/azure-iis-errors-reference?view=aspnetcore-10.0)
- [Handle errors in ASP.NET Core APIs](error-handling-api?view=aspnetcore-10.0)

By [Tom Dykstra](https://github.com/tdykstra/)

This article covers common approaches to handling errors in ASP.NET Core web apps. See also [Handle errors in ASP.NET Core APIs](error-handling-api?view=aspnetcore-10.0).

## Developer exception page

The *Developer Exception Page* displays detailed information about unhandled request exceptions. ASP.NET Core apps enable the developer exception page by default when both:

- Running in the [`Development` environment](environments?view=aspnetcore-10.0).
- App created with the current templates, that is, using [WebApplication.CreateBuilder](/en-us/dotnet/api/microsoft.aspnetcore.builder.webapplication.createbuilder). Apps created using the [`WebHost.CreateDefaultBuilder`](/en-us/dotnet/api/microsoft.aspnetcore.webhost.createdefaultbuilder#microsoft-aspnetcore-webhost-createdefaultbuilder) must enable the developer exception page by calling `app.UseDeveloperExceptionPage` in `Configure`.

The developer exception page runs early in the middleware pipeline, so that it can catch unhandled exceptions thrown in middleware that follows.

Detailed exception information shouldn't be displayed publicly when the app runs in the `Production` environment. For more information on configuring environments, see [ASP.NET Core runtime environments](environments?view=aspnetcore-10.0).

The Developer Exception Page can include the following information about the exception and the request:

- Stack trace
- Query string parameters, if any
- Cookies, if any
- Headers

The Developer Exception Page isn't guaranteed to provide any information. Use [Logging](logging/?view=aspnetcore-10.0) for complete error information.

## Exception handler page

To configure a custom error handling page for the [`Production` environment](environments?view=aspnetcore-10.0), call [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). This exception handling middleware:

- Catches and logs unhandled exceptions.
- Re-executes the request in an alternate pipeline using the path indicated. The request isn't re-executed if the response has started. The template-generated code re-executes the request using the `/Error` path.

Warning

If the alternate pipeline throws an exception of its own, exception handling middleware rethrows the original exception.

Since this middleware can re-execute the request pipeline:

- Middlewares need to handle reentrancy with the same request. This normally means either cleaning up their state after calling `_next` or caching their processing on the `HttpContext` to avoid redoing it. When dealing with the request body, this either means buffering or caching the results like the Form reader.
- For the [UseExceptionHandler(IApplicationBuilder, String)](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler#microsoft-aspnetcore-builder-exceptionhandlerextensions-useexceptionhandler(microsoft-aspnetcore-builder-iapplicationbuilder-system-string)) overload that is used in templates, only the request path is modified, and the route data is cleared. Request data such as headers, method, and items are all reused as-is.
- Scoped services remain the same.

In the following example, [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler) adds the exception handling middleware in non-`Development` environments:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}
```

The Razor Pages app template provides an Error page (`.cshtml`) and [PageModel](/en-us/dotnet/api/microsoft.aspnetcore.mvc.razorpages.pagemodel) class (`ErrorModel`) in the *Pages* folder. For an MVC app, the project template includes an `Error` action method and an Error view for the Home controller.

The exception handling middleware re-executes the request using the *original* HTTP method. If an error handler endpoint is restricted to a specific set of HTTP methods, it runs only for those HTTP methods. For example, an MVC controller action that uses the `[HttpGet]` attribute runs only for GET requests. To ensure that *all* requests reach the custom error handling page, don't restrict them to a specific set of HTTP methods.

To handle exceptions differently based on the original HTTP method:

- For Razor Pages, create multiple handler methods. For example, use `OnGet` to handle GET exceptions and use `OnPost` to handle POST exceptions.
- For MVC, apply HTTP verb attributes to multiple actions. For example, use `[HttpGet]` to handle GET exceptions and use `[HttpPost]` to handle POST exceptions.

To allow unauthenticated users to view the custom error handling page, ensure that it supports anonymous access.

### Access the exception

Use [IExceptionHandlerPathFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandlerpathfeature) to access the exception and the original request path in an error handler. The following example uses `IExceptionHandlerPathFeature` to get more information about the exception that was thrown:

```
[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
[IgnoreAntiforgeryToken]
public class ErrorModel : PageModel
{
    public string? RequestId { get; set; }

    public bool ShowRequestId => !string.IsNullOrEmpty(RequestId);

    public string? ExceptionMessage { get; set; }

    public void OnGet()
    {
        RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;

        var exceptionHandlerPathFeature =
            HttpContext.Features.Get<IExceptionHandlerPathFeature>();

        if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
        {
            ExceptionMessage = "The file was not found.";
        }

        if (exceptionHandlerPathFeature?.Path == "/")
        {
            ExceptionMessage ??= string.Empty;
            ExceptionMessage += " Page: Home.";
        }
    }
}
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

## Exception handler lambda

An alternative to a [custom exception handler page](#exception-handler-page) is to provide a lambda to [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). Using a lambda allows access to the error before returning the response.

The following code uses a lambda for exception handling:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler(exceptionHandlerApp =>
    {
        exceptionHandlerApp.Run(async context =>
        {
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;

            // using static System.Net.Mime.MediaTypeNames;
            context.Response.ContentType = Text.Plain;

            await context.Response.WriteAsync("An exception was thrown.");

            var exceptionHandlerPathFeature =
                context.Features.Get<IExceptionHandlerPathFeature>();

            if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
            {
                await context.Response.WriteAsync(" The file was not found.");
            }

            if (exceptionHandlerPathFeature?.Path == "/")
            {
                await context.Response.WriteAsync(" Page: Home.");
            }
        });
    });

    app.UseHsts();
}
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

## IExceptionHandler

[IExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandler) is an interface that gives the developer a callback for handling known exceptions in a central location.

`IExceptionHandler` implementations are registered by calling [`IServiceCollection.AddExceptionHandler<T>`](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.exceptionhandlerservicecollectionextensions.addexceptionhandler). The lifetime of an `IExceptionHandler` instance is singleton. Multiple implementations can be added, and they're called in the order registered.

Important

Registering an `IExceptionHandler` implementation isn't sufficient on its own. Registered handlers are invoked by the exception handling middleware, so the app must also add that middleware by calling [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). If `UseExceptionHandler` isn't called, the registered `IExceptionHandler` implementations are never called.

Exception handling middleware iterates through registered exception handlers in order until one returns `true` from `TryHandleAsync`, indicating that the exception has been handled. If an exception handler handles an exception, it can return `true` to stop processing. If an exception isn't handled by any exception handler, then control falls back to the default behavior and options from the middleware.

Note

In .NET 8 and .NET 9, the exception handling middleware logs the exception and emits metrics even when an `IExceptionHandler` implementation returns `true` from `TryHandleAsync`. If the handler does its own logging, the exception is recorded twice: once under the `Microsoft.AspNetCore.Diagnostics.ExceptionHandlerMiddleware` category and once under the handler's category. To log it only from the handler, filter out the middleware category in configuration:

```
{
  "Logging": {
    "LogLevel": {
      "Microsoft.AspNetCore.Diagnostics.ExceptionHandlerMiddleware": "None"
    }
  }
}
```

Starting in .NET 10, diagnostics are suppressed by default for handled exceptions. See [SuppressDiagnosticsCallback](error-handling?view=aspnetcore-10.0#suppressdiagnosticscallback).

The following example shows an `IExceptionHandler` implementation:

```
using Microsoft.AspNetCore.Diagnostics;

namespace ErrorHandlingSample
{
    public class CustomExceptionHandler : IExceptionHandler
    {
        private readonly ILogger<CustomExceptionHandler> logger;
        public CustomExceptionHandler(ILogger<CustomExceptionHandler> logger)
        {
            this.logger = logger;
        }
        public ValueTask<bool> TryHandleAsync(
            HttpContext httpContext,
            Exception exception,
            CancellationToken cancellationToken)
        {
            var exceptionMessage = exception.Message;
            logger.LogError(
                "Error Message: {exceptionMessage}, Time of occurrence {time}",
                exceptionMessage, DateTime.UtcNow);
            // Return false to continue with the default behavior
            // - or - return true to signal that this exception is handled
            return ValueTask.FromResult(false);
        }
    }
}
```

The following example shows how to register an `IExceptionHandler` implementation for dependency injection and add the exception handling middleware that calls it:

```
using ErrorHandlingSample;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDatabaseDeveloperPageExceptionFilter();
builder.Services.AddRazorPages();
builder.Services.AddExceptionHandler<CustomExceptionHandler>();

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

// Remaining Program.cs code omitted for brevity
```

### Configure `UseExceptionHandler` when using `IExceptionHandler`

The exception handling middleware requires a fallback for exceptions that no `IExceptionHandler` handles. If none is configured, calling `app.UseExceptionHandler()` with no arguments throws at startup:

`System.InvalidOperationException: An error occurred when configuring the exception handler middleware. Either the 'ExceptionHandlingPath' or the 'ExceptionHandler' property must be set in 'UseExceptionHandler()'.`

Use any one of the following to satisfy the requirement:

- Specify an error path: `app.UseExceptionHandler("/Error");`
- Enable problem details: call `builder.Services.AddProblemDetails();` and then `app.UseExceptionHandler();`
- Supply a fallback handler: `app.UseExceptionHandler(exceptionHandlerApp => { ... });`

The `IExceptionHandler` implementations still run first in all of these cases. The configured path, problem details response, or fallback handler is used only when every `TryHandleAsync` returns `false`.

If an `IExceptionHandler` returns `true` without writing a response or setting a status code, the response ends up as `404 Not Found` and the middleware logs:

`The exception handler configured on ExceptionHandlerOptions produced a 404 status response.`

An `IExceptionHandler` that returns `true` should write the complete response, including the status code. For example, set `httpContext.Response.StatusCode` and write the body, or call `IProblemDetailsService.TryWriteAsync`. If a 404 response is intentional, set [AllowStatusCode404Response](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandleroptions.allowstatuscode404response#microsoft-aspnetcore-builder-exceptionhandleroptions-allowstatuscode404response) to `true`.

When the preceding code runs in the `Development` environment:

- The `CustomExceptionHandler` is called first to handle an exception.
- After logging the exception, the `TryHandleAsync` method returns `false`, so the [developer exception page](#developer-exception-page) is shown.

In other environments:

- The `CustomExceptionHandler` is called first to handle an exception.
- After logging the exception, the `TryHandleAsync` method returns `false`, so the [`/Error` page](#exception-handler-page) is shown.

If `TryHandleAsync` returns `true` instead:

- The remaining `IExceptionHandler` implementations aren't called.
- The exception handler page, path, or lambda configured on `UseExceptionHandler` isn't used. The handler is responsible for writing the entire response.

## UseStatusCodePages

By default, an ASP.NET Core app doesn't provide a status code page for HTTP error status codes, such as *404 - Not Found*. When the app sets an HTTP 400-599 error status code that doesn't have a body, it returns the status code and an empty response body. To enable default text-only handlers for common error status codes, call [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) in `Program.cs`:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePages();
```

Call `UseStatusCodePages` before request handling middleware. For example, call `UseStatusCodePages` before the static file middleware and the endpoints middleware.

When `UseStatusCodePages` isn't used, navigating to a URL without an endpoint returns a browser-dependent error message indicating the endpoint can't be found. When `UseStatusCodePages` is called, the browser returns the following response:

```
Status Code: 404; Not Found
```

`UseStatusCodePages` isn't typically used in production because it returns a message that isn't useful to users.

Note

The status code pages middleware does **not** catch exceptions. To provide a custom error handling page, use the [exception handler page](#exception-handler-page).

### UseStatusCodePages with format string

To customize the response content type and text, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a content type and format string:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

// using static System.Net.Mime.MediaTypeNames;
app.UseStatusCodePages(Text.Plain, "Status Code Page: {0}");
```

In the preceding code, `{0}` is a placeholder for the error code.

`UseStatusCodePages` with a format string isn't typically used in production because it returns a message that isn't useful to users.

### UseStatusCodePages with lambda

To specify custom error-handling and response-writing code, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a lambda expression:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePages(async statusCodeContext =>
{
    // using static System.Net.Mime.MediaTypeNames;
    statusCodeContext.HttpContext.Response.ContentType = Text.Plain;

    await statusCodeContext.HttpContext.Response.WriteAsync(
        $"Status Code Page: {statusCodeContext.HttpContext.Response.StatusCode}");
});
```

`UseStatusCodePages` with a lambda isn't typically used in production because it returns a message that isn't useful to users.

### UseStatusCodePagesWithRedirects

The [UseStatusCodePagesWithRedirects](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithredirects) extension method:

- Sends a [302 - Found](https://developer.mozilla.org/docs/Web/HTTP/Status/302) status code to the client.
- Redirects the client to the error handling endpoint provided in the URL template. The error handling endpoint typically displays error information and returns HTTP 200.

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePagesWithRedirects("/StatusCode/{0}");
```

The URL template can include a `{0}` placeholder for the status code, as shown in the preceding code. If the URL template starts with `~` (tilde), the `~` is replaced by the app's `PathBase`. When specifying an endpoint in the app, create an MVC view or Razor page for the endpoint.

This method is commonly used when the app:

- Should redirect the client to a different endpoint, usually in cases where a different app processes the error. For web apps, the client's browser address bar reflects the redirected endpoint.
- Shouldn't preserve and return the original status code with the initial redirect response.

### UseStatusCodePagesWithReExecute

The [UseStatusCodePagesWithReExecute](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithreexecute) extension method:

- Generates the response body by re-executing the request pipeline using an alternate path.
- Does not alter the status code before or after re-executing the pipeline.

The new pipeline execution may alter the response's status code, as the new pipeline has full control of the status code. If the new pipeline does not alter the status code, the original status code will be sent to the client.

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePagesWithReExecute("/StatusCode/{0}");
```

If an endpoint within the app is specified, create an MVC view or Razor page for the endpoint.

This method is commonly used when the app should:

- Process the request without redirecting to a different endpoint. For web apps, the client's browser address bar reflects the originally requested endpoint.
- Preserve and return the original status code with the response.

The URL template must start with `/` and may include a placeholder `{0}` for the status code. To pass the status code as a query-string parameter, pass a second argument into `UseStatusCodePagesWithReExecute`. For example:

```
var app = builder.Build();  
app.UseStatusCodePagesWithReExecute("/StatusCode", "?statusCode={0}");
```

The endpoint that processes the error can get the original URL that generated the error, as shown in the following example:

```
[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
public class StatusCodeModel : PageModel
{
    public int OriginalStatusCode { get; set; }

    public string? OriginalPathAndQuery { get; set; }

    public void OnGet(int statusCode)
    {
        OriginalStatusCode = statusCode;

        var statusCodeReExecuteFeature =
            HttpContext.Features.Get<IStatusCodeReExecuteFeature>();

        if (statusCodeReExecuteFeature is not null)
        {
            OriginalPathAndQuery = $"{statusCodeReExecuteFeature.OriginalPathBase}"
                                    + $"{statusCodeReExecuteFeature.OriginalPath}"
                                    + $"{statusCodeReExecuteFeature.OriginalQueryString}";

        }
    }
}
```

Since this middleware can re-execute the request pipeline:

- Middlewares need to handle reentrancy with the same request. This normally means either cleaning up their state after calling `_next` or caching their processing on the `HttpContext` to avoid redoing it. When dealing with the request body, this either means buffering or caching the results like the Form reader.
- Scoped services remain the same.

## Disable status code pages

To disable status code pages for an MVC controller or action method, use the [[SkipStatusCodePages]](/en-us/dotnet/api/microsoft.aspnetcore.mvc.skipstatuscodepagesattribute) attribute.

To disable status code pages for specific requests in a Razor Pages handler method or in an MVC controller, use [IStatusCodePagesFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.istatuscodepagesfeature):

```
public void OnGet()
{
    var statusCodePagesFeature =
        HttpContext.Features.Get<IStatusCodePagesFeature>();

    if (statusCodePagesFeature is not null)
    {
        statusCodePagesFeature.Enabled = false;
    }
}
```

## Exception-handling code

Code in exception handling pages can also throw exceptions. Production error pages should be tested thoroughly and take extra care to avoid throwing exceptions of their own.

### Response headers

Once the headers for a response are sent:

- The app can't change the response's status code.
- Any exception pages or handlers can't run. The response must be completed or the connection aborted.

## Server exception handling

In addition to the exception handling logic in an app, the [HTTP server implementation](servers/?view=aspnetcore-10.0) can handle some exceptions. If the server catches an exception before response headers are sent, the server sends a `500 - Internal Server Error` response without a response body. If the server catches an exception after response headers are sent, the server closes the connection. Requests that aren't handled by the app are handled by the server. Any exception that occurs when the server is handling the request is handled by the server's exception handling. The app's custom error pages, exception handling middleware, and filters don't affect this behavior.

## Startup exception handling

Only the hosting layer can handle exceptions that take place during app startup. The host can be configured to [capture startup errors](host/web-host?view=aspnetcore-10.0#capture-startup-errors) and [capture detailed errors](host/web-host?view=aspnetcore-10.0#detailed-errors).

The hosting layer can show an error page for a captured startup error only if the error occurs after host address/port binding. If binding fails:

- The hosting layer logs a critical exception.
- The dotnet process crashes.
- No error page is displayed when the HTTP server is [Kestrel](servers/kestrel?view=aspnetcore-10.0).

When running on [IIS](/en-us/iis) (or Azure App Service) or [IIS Express](/en-us/iis/extensions/introduction-to-iis-express/iis-express-overview), a *502.5 - Process Failure* is returned by the [ASP.NET Core Module](../host-and-deploy/aspnet-core-module?view=aspnetcore-10.0) if the process can't start. For more information, see [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0).

## Database error page

The Database developer page exception filter [AddDatabaseDeveloperPageExceptionFilter](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.databasedeveloperpageexceptionfilterserviceextensions.adddatabasedeveloperpageexceptionfilter) captures database-related exceptions that can be resolved by using Entity Framework Core migrations. When these exceptions occur, an HTML response is generated with details of possible actions to resolve the issue. This page is enabled only in the `Development` environment. The following code adds the Database developer page exception filter:

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDatabaseDeveloperPageExceptionFilter();
builder.Services.AddRazorPages();
```

## Exception filters

In MVC apps, exception filters can be configured globally or on a per-controller or per-action basis. In Razor Pages apps, they can be configured globally or per page model. These filters handle any unhandled exceptions that occur during the execution of a controller action or another filter. For more information, see [Filters in ASP.NET Core](../mvc/controllers/filters?view=aspnetcore-10.0#exception-filters).

Exception filters are useful for trapping exceptions that occur within MVC actions, but they're not as flexible as the built-in [exception handling middleware](https://github.com/dotnet/aspnetcore/blob/main/src/Middleware/Diagnostics/src/ExceptionHandler/ExceptionHandlerMiddleware.cs), [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). We recommend using `UseExceptionHandler`, unless you need to perform error handling differently based on which MVC action is chosen.

## Model state errors

For information about how to handle model state errors, see [Model binding](../mvc/models/model-binding?view=aspnetcore-10.0) and [Model validation](../mvc/models/validation?view=aspnetcore-10.0).

## Problem details

[Problem Details](https://www.rfc-editor.org/rfc/rfc7807.html) are not the only response format to describe an HTTP API error, however, they are commonly used to report errors for HTTP APIs.

The problem details service implements the [IProblemDetailsService](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice) interface, which supports creating problem details in ASP.NET Core. The [AddProblemDetails(IServiceCollection)](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.problemdetailsservicecollectionextensions.addproblemdetails#microsoft-extensions-dependencyinjection-problemdetailsservicecollectionextensions-addproblemdetails(microsoft-extensions-dependencyinjection-iservicecollection)) extension method on [IServiceCollection](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.iservicecollection) registers the default `IProblemDetailsService` implementation.

In ASP.NET Core apps, the following middleware generates problem details HTTP responses when `AddProblemDetails` is called, except when the [`Accept` request HTTP header](https://developer.mozilla.org/docs/Web/HTTP/Headers/Accept) doesn't include one of the content types supported by the registered [IProblemDetailsWriter](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailswriter) (default: `application/json`):

- [ExceptionHandlerMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.exceptionhandlermiddleware): Generates a problem details response when a custom handler is not defined.
- [StatusCodePagesMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.statuscodepagesmiddleware): Generates a problem details response by default.
- [DeveloperExceptionPageMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.developerexceptionpagemiddleware): Generates a problem details response in development when the `Accept` request HTTP header doesn't include `text/html`.

The following code configures the app to generate a problem details response for all HTTP client and server error responses that ***don't have a body content yet***:

```
builder.Services.AddProblemDetails();

var app = builder.Build();        

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler();
    app.UseHsts();
}

app.UseStatusCodePages();
```

The next section shows how to customize the problem details response body.

### Customize problem details

The automatic creation of a `ProblemDetails` can be customized using any of the following options:

1. Use [`ProblemDetailsOptions.CustomizeProblemDetails`](#customizeproblemdetails-operation)
2. Use a custom [`IProblemDetailsWriter`](#custom-iproblemdetailswriter)
3. Call the [`IProblemDetailsService` in a middleware](#problem-details-from-middleware)

#### `CustomizeProblemDetails` operation

The generated problem details can be customized using [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails), and the customizations are applied to all auto-generated problem details.

The following code uses [ProblemDetailsOptions](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions) to set [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails):

```
builder.Services.AddProblemDetails(options =>
    options.CustomizeProblemDetails = ctx =>
            ctx.ProblemDetails.Extensions.Add("nodeId", Environment.MachineName));

var app = builder.Build();        

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler();
    app.UseHsts();
}

app.UseStatusCodePages();
```

For example, an [`HTTP Status 400 Bad Request`](https://developer.mozilla.org/docs/Web/HTTP/Status/400) endpoint result produces the following problem details response body:

```
{
  "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
  "title": "Bad Request",
  "status": 400,
  "nodeId": "my-machine-name"
}
```

#### Custom `IProblemDetailsWriter`

An [IProblemDetailsWriter](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailswriter) implementation can be created for advanced customizations.

```
public class SampleProblemDetailsWriter : IProblemDetailsWriter
{
    // Indicates that only responses with StatusCode == 400
    // are handled by this writer. All others are
    // handled by different registered writers if available.
    public bool CanWrite(ProblemDetailsContext context)
        => context.HttpContext.Response.StatusCode == 400;

    public ValueTask WriteAsync(ProblemDetailsContext context)
    {
        // Additional customizations.

        // Write to the response.
        var response = context.HttpContext.Response;
        return new ValueTask(response.WriteAsJsonAsync(context.ProblemDetails));
    }
}
```

***Note:*** When using a custom `IProblemDetailsWriter`, the custom `IProblemDetailsWriter` must be registered before calling [AddRazorPages](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addrazorpages), [AddControllers](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addcontrollers), [AddControllersWithViews](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addcontrollerswithviews), or [AddMvc](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addmvc):

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddTransient<IProblemDetailsWriter, SampleProblemDetailsWriter>();

var app = builder.Build();

// Middleware to handle writing problem details to the response.
app.Use(async (context, next) =>
{
    await next(context);
    var mathErrorFeature = context.Features.Get<MathErrorFeature>();
    if (mathErrorFeature is not null)
    {
        if (context.RequestServices.GetService<IProblemDetailsWriter>() is
            { } problemDetailsService)
        {

            if (problemDetailsService.CanWrite(new ProblemDetailsContext() { HttpContext = context }))
            {
                (string Detail, string Type) details = mathErrorFeature.MathError switch
                {
                    MathErrorType.DivisionByZeroError => ("Divison by zero is not defined.",
                        "https://en.wikipedia.org/wiki/Division_by_zero"),
                    _ => ("Negative or complex numbers are not valid input.",
                        "https://en.wikipedia.org/wiki/Square_root")
                };

                await problemDetailsService.WriteAsync(new ProblemDetailsContext
                {
                    HttpContext = context,
                    ProblemDetails =
                    {
                        Title = "Bad Input",
                        Detail = details.Detail,
                        Type = details.Type
                    }
                });
            }
        }
    }
});

// /divide?numerator=2&denominator=4
app.MapGet("/divide", (HttpContext context, double numerator, double denominator) =>
{
    if (denominator == 0)
    {
        var errorType = new MathErrorFeature
        {
            MathError = MathErrorType.DivisionByZeroError
        };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(numerator / denominator);
});

// /squareroot?radicand=16
app.MapGet("/squareroot", (HttpContext context, double radicand) =>
{
    if (radicand < 0)
    {
        var errorType = new MathErrorFeature
        {
            MathError = MathErrorType.NegativeRadicandError
        };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(Math.Sqrt(radicand));
});

app.Run();
```

#### Problem details from Middleware

An alternative approach to using [ProblemDetailsOptions](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions) with [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails) is to set the [ProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailscontext.problemdetails#microsoft-aspnetcore-http-problemdetailscontext-problemdetails) in middleware. A problem details response can be written by calling [`IProblemDetailsService.WriteAsync`](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice.writeasync?view=aspnetcore-7.0&preserve-view=true):

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseHttpsRedirection();
app.UseStatusCodePages();

// Middleware to handle writing problem details to the response.
app.Use(async (context, next) =>
{
    await next(context);
    var mathErrorFeature = context.Features.Get<MathErrorFeature>();
    if (mathErrorFeature is not null)
    {
        if (context.RequestServices.GetService<IProblemDetailsService>() is
                                                           { } problemDetailsService)
        {
            (string Detail, string Type) details = mathErrorFeature.MathError switch
            {
                MathErrorType.DivisionByZeroError => ("Divison by zero is not defined.",
                "https://en.wikipedia.org/wiki/Division_by_zero"),
                _ => ("Negative or complex numbers are not valid input.", 
                "https://en.wikipedia.org/wiki/Square_root")
            };

            await problemDetailsService.WriteAsync(new ProblemDetailsContext
            {
                HttpContext = context,
                ProblemDetails =
                {
                    Title = "Bad Input",
                    Detail = details.Detail,
                    Type = details.Type
                }
            });
        }
    }
});

// /divide?numerator=2&denominator=4
app.MapGet("/divide", (HttpContext context, double numerator, double denominator) =>
{
    if (denominator == 0)
    {
        var errorType = new MathErrorFeature { MathError =
                                               MathErrorType.DivisionByZeroError };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(numerator / denominator);
});

// /squareroot?radicand=16
app.MapGet("/squareroot", (HttpContext context, double radicand) =>
{
    if (radicand < 0)
    {
        var errorType = new MathErrorFeature { MathError =
                                               MathErrorType.NegativeRadicandError };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(Math.Sqrt(radicand));
});

app.MapControllers();

app.Run();
```

In the preceding code, the Minimal API endpoints `/divide` and `/squareroot` return the expected custom problem response on error input.

The API controller endpoints return the default problem response on error input, not the custom problem response. The default problem response is returned because the API controller has written to the response stream, [Problem details for error status codes](/en-us/aspnet/core/web-api/#problem-details-for-error-status-codes-1), before [`IProblemDetailsService.WriteAsync`](https://github.com/dotnet/aspnetcore/blob/ce2db7ea0b161fc5eb35710fca6feeafeeac37bc/src/Http/Http.Extensions/src/ProblemDetailsService.cs#L24) is called and the response is **not** written again.

The following `ValuesController` returns [BadRequestResult](/en-us/dotnet/api/microsoft.aspnetcore.mvc.badrequestresult), which writes to the response stream and therefore prevents the custom problem response from being returned.

```
[Route("api/[controller]/[action]")]
[ApiController]
public class ValuesController : ControllerBase
{
    // /api/values/divide/1/2
    [HttpGet("{Numerator}/{Denominator}")]
    public IActionResult Divide(double Numerator, double Denominator)
    {
        if (Denominator == 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.DivisionByZeroError
            };
            HttpContext.Features.Set(errorType);
            return BadRequest();
        }

        return Ok(Numerator / Denominator);
    }

    // /api/values/squareroot/4
    [HttpGet("{radicand}")]
    public IActionResult Squareroot(double radicand)
    {
        if (radicand < 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.NegativeRadicandError
            };
            HttpContext.Features.Set(errorType);
            return BadRequest();
        }

        return Ok(Math.Sqrt(radicand));
    }

}
```

The following `Values3Controller` returns [`ControllerBase.Problem`](/en-us/dotnet/api/microsoft.aspnetcore.mvc.controllerbase.problem) so the expected custom problem result is returned:

```
[Route("api/[controller]/[action]")]
[ApiController]
public class Values3Controller : ControllerBase
{
    // /api/values3/divide/1/2
    [HttpGet("{Numerator}/{Denominator}")]
    public IActionResult Divide(double Numerator, double Denominator)
    {
        if (Denominator == 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.DivisionByZeroError
            };
            HttpContext.Features.Set(errorType);
            return Problem(
                title: "Bad Input",
                detail: "Divison by zero is not defined.",
                type: "https://en.wikipedia.org/wiki/Division_by_zero",
                statusCode: StatusCodes.Status400BadRequest
                );
        }

        return Ok(Numerator / Denominator);
    }

    // /api/values3/squareroot/4
    [HttpGet("{radicand}")]
    public IActionResult Squareroot(double radicand)
    {
        if (radicand < 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.NegativeRadicandError
            };
            HttpContext.Features.Set(errorType);
            return Problem(
                title: "Bad Input",
                detail: "Negative or complex numbers are not valid input.",
                type: "https://en.wikipedia.org/wiki/Square_root",
                statusCode: StatusCodes.Status400BadRequest
                );
        }

        return Ok(Math.Sqrt(radicand));
    }

}
```

## Produce a ProblemDetails payload for exceptions

Consider the following app:

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}

app.MapControllers();
app.Run();
```

In non-development environments, when an exception occurs, the following is a standard [ProblemDetails response](https://datatracker.ietf.org/doc/html/rfc7807) that is returned to the client:

```
{
"type":"https://tools.ietf.org/html/rfc7231#section-6.6.1",
"title":"An error occurred while processing your request.",
"status":500,"traceId":"00-b644<snip>-00"
}
```

For most apps, the preceding code is all that's needed for exceptions. However, the following section shows how to get more detailed problem responses.

An alternative to a [custom exception handler page](error-handling?view=aspnetcore-10.0#exception-handler-page) is to provide a lambda to [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). Using a lambda allows access to the error and writing a problem details response with [`IProblemDetailsService.WriteAsync`](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice.writeasync?view=aspnetcore-7.0&preserve-view=true):

```
using Microsoft.AspNetCore.Diagnostics;
using static System.Net.Mime.MediaTypeNames;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}
else
{
    app.UseExceptionHandler(exceptionHandlerApp =>
    {
        exceptionHandlerApp.Run(async context =>
        {
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;
            context.Response.ContentType = Text.Plain;

            var title = "Bad Input";
            var detail = "Invalid input";
            var type = "https://errors.example.com/badInput";

            if (context.RequestServices.GetService<IProblemDetailsService>() is
                { } problemDetailsService)
            {
                var exceptionHandlerFeature =
               context.Features.Get<IExceptionHandlerFeature>();

                var exceptionType = exceptionHandlerFeature?.Error;
                if (exceptionType != null &&
                   exceptionType.Message.Contains("infinity"))
                {
                    title = "Argument exception";
                    detail = "Invalid input";
                    type = "https://errors.example.com/argumentException";
                }

                await problemDetailsService.WriteAsync(new ProblemDetailsContext
                {
                    HttpContext = context,
                    ProblemDetails =
                {
                    Title = title,
                    Detail = detail,
                    Type = type
                }
                });
            }
        });
    });
}

app.MapControllers();
app.Run();
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

An alternative approach to generate problem details is to use the third-party NuGet package [Hellang.Middleware.ProblemDetails](https://www.nuget.org/packages/Hellang.Middleware.ProblemDetails/) that can be used to map exceptions and client errors to problem details.

## Additional resources

- [View or download sample code](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples) ([how to download](./?view=aspnetcore-10.0#how-to-download-a-sample))
- [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0)
- [Common error troubleshooting for Azure App Service and IIS with ASP.NET Core](../host-and-deploy/azure-iis-errors-reference?view=aspnetcore-10.0)
- [Handle errors in ASP.NET Core APIs](error-handling-api?view=aspnetcore-10.0)
- [Handle errors in ASP.NET Core APIs](error-handling-api?view=aspnetcore-10.0).

By [Tom Dykstra](https://github.com/tdykstra/)

This article covers common approaches to handling errors in ASP.NET Core web apps. See also [Handle errors in ASP.NET Core APIs](error-handling-api?view=aspnetcore-10.0).

## Developer exception page

The *Developer Exception Page* displays detailed information about unhandled request exceptions. ASP.NET Core apps enable the developer exception page by default when both:

- Running in the [`Development` environment](environments?view=aspnetcore-10.0).
- App created with the current templates, that is, using [WebApplication.CreateBuilder](/en-us/dotnet/api/microsoft.aspnetcore.builder.webapplication.createbuilder). Apps created using the [`WebHost.CreateDefaultBuilder`](/en-us/dotnet/api/microsoft.aspnetcore.webhost.createdefaultbuilder#microsoft-aspnetcore-webhost-createdefaultbuilder) must enable the developer exception page by calling `app.UseDeveloperExceptionPage` in `Configure`.

The developer exception page runs early in the middleware pipeline, so that it can catch unhandled exceptions thrown in middleware that follows.

Detailed exception information shouldn't be displayed publicly when the app runs in the `Production` environment. For more information on configuring environments, see [ASP.NET Core runtime environments](environments?view=aspnetcore-10.0).

The Developer Exception Page can include the following information about the exception and the request:

- Stack trace
- Query string parameters, if any
- Cookies, if any
- Headers

The Developer Exception Page isn't guaranteed to provide any information. Use [Logging](logging/?view=aspnetcore-10.0) for complete error information.

## Exception handler page

To configure a custom error handling page for the [`Production` environment](environments?view=aspnetcore-10.0), call [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). This exception handling middleware:

- Catches and logs unhandled exceptions.
- Re-executes the request in an alternate pipeline using the path indicated. The request isn't re-executed if the response has started. The template-generated code re-executes the request using the `/Error` path.

Warning

If the alternate pipeline throws an exception of its own, exception handling middleware rethrows the original exception.

Since this middleware can re-execute the request pipeline:

- Middlewares need to handle reentrancy with the same request. This normally means either cleaning up their state after calling `_next` or caching their processing on the `HttpContext` to avoid redoing it. When dealing with the request body, this either means buffering or caching the results like the Form reader.
- For the [UseExceptionHandler(IApplicationBuilder, String)](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler#microsoft-aspnetcore-builder-exceptionhandlerextensions-useexceptionhandler(microsoft-aspnetcore-builder-iapplicationbuilder-system-string)) overload that is used in templates, only the request path is modified, and the route data is cleared. Request data such as headers, method, and items are all reused as-is.
- Scoped services remain the same.

In the following example, [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler) adds the exception handling middleware in non-`Development` environments:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}
```

The Razor Pages app template provides an Error page (`.cshtml`) and [PageModel](/en-us/dotnet/api/microsoft.aspnetcore.mvc.razorpages.pagemodel) class (`ErrorModel`) in the *Pages* folder. For an MVC app, the project template includes an `Error` action method and an Error view for the Home controller.

The exception handling middleware re-executes the request using the *original* HTTP method. If an error handler endpoint is restricted to a specific set of HTTP methods, it runs only for those HTTP methods. For example, an MVC controller action that uses the `[HttpGet]` attribute runs only for GET requests. To ensure that *all* requests reach the custom error handling page, don't restrict them to a specific set of HTTP methods.

To handle exceptions differently based on the original HTTP method:

- For Razor Pages, create multiple handler methods. For example, use `OnGet` to handle GET exceptions and use `OnPost` to handle POST exceptions.
- For MVC, apply HTTP verb attributes to multiple actions. For example, use `[HttpGet]` to handle GET exceptions and use `[HttpPost]` to handle POST exceptions.

To allow unauthenticated users to view the custom error handling page, ensure that it supports anonymous access.

### Access the exception

Use [IExceptionHandlerPathFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandlerpathfeature) to access the exception and the original request path in an error handler. The following example uses `IExceptionHandlerPathFeature` to get more information about the exception that was thrown:

```
[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
[IgnoreAntiforgeryToken]
public class ErrorModel : PageModel
{
    public string? RequestId { get; set; }

    public bool ShowRequestId => !string.IsNullOrEmpty(RequestId);

    public string? ExceptionMessage { get; set; }

    public void OnGet()
    {
        RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;

        var exceptionHandlerPathFeature =
            HttpContext.Features.Get<IExceptionHandlerPathFeature>();

        if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
        {
            ExceptionMessage = "The file was not found.";
        }

        if (exceptionHandlerPathFeature?.Path == "/")
        {
            ExceptionMessage ??= string.Empty;
            ExceptionMessage += " Page: Home.";
        }
    }
}
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

## Exception handler lambda

An alternative to a [custom exception handler page](#exception-handler-page) is to provide a lambda to [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). Using a lambda allows access to the error before returning the response.

The following code uses a lambda for exception handling:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler(exceptionHandlerApp =>
    {
        exceptionHandlerApp.Run(async context =>
        {
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;

            // using static System.Net.Mime.MediaTypeNames;
            context.Response.ContentType = Text.Plain;

            await context.Response.WriteAsync("An exception was thrown.");

            var exceptionHandlerPathFeature =
                context.Features.Get<IExceptionHandlerPathFeature>();

            if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
            {
                await context.Response.WriteAsync(" The file was not found.");
            }

            if (exceptionHandlerPathFeature?.Path == "/")
            {
                await context.Response.WriteAsync(" Page: Home.");
            }
        });
    });

    app.UseHsts();
}
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

## UseStatusCodePages

By default, an ASP.NET Core app doesn't provide a status code page for HTTP error status codes, such as *404 - Not Found*. When the app sets an HTTP 400-599 error status code that doesn't have a body, it returns the status code and an empty response body. To enable default text-only handlers for common error status codes, call [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) in `Program.cs`:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePages();
```

Call `UseStatusCodePages` before request handling middleware. For example, call `UseStatusCodePages` before the static file middleware and the endpoints middleware.

When `UseStatusCodePages` isn't used, navigating to a URL without an endpoint returns a browser-dependent error message indicating the endpoint can't be found. When `UseStatusCodePages` is called, the browser returns the following response:

```
Status Code: 404; Not Found
```

`UseStatusCodePages` isn't typically used in production because it returns a message that isn't useful to users.

Note

The status code pages middleware does **not** catch exceptions. To provide a custom error handling page, use the [exception handler page](#exception-handler-page).

### UseStatusCodePages with format string

To customize the response content type and text, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a content type and format string:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

// using static System.Net.Mime.MediaTypeNames;
app.UseStatusCodePages(Text.Plain, "Status Code Page: {0}");
```

In the preceding code, `{0}` is a placeholder for the error code.

`UseStatusCodePages` with a format string isn't typically used in production because it returns a message that isn't useful to users.

### UseStatusCodePages with lambda

To specify custom error-handling and response-writing code, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a lambda expression:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePages(async statusCodeContext =>
{
    // using static System.Net.Mime.MediaTypeNames;
    statusCodeContext.HttpContext.Response.ContentType = Text.Plain;

    await statusCodeContext.HttpContext.Response.WriteAsync(
        $"Status Code Page: {statusCodeContext.HttpContext.Response.StatusCode}");
});
```

`UseStatusCodePages` with a lambda isn't typically used in production because it returns a message that isn't useful to users.

### UseStatusCodePagesWithRedirects

The [UseStatusCodePagesWithRedirects](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithredirects) extension method:

- Sends a [302 - Found](https://developer.mozilla.org/docs/Web/HTTP/Status/302) status code to the client.
- Redirects the client to the error handling endpoint provided in the URL template. The error handling endpoint typically displays error information and returns HTTP 200.

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePagesWithRedirects("/StatusCode/{0}");
```

The URL template can include a `{0}` placeholder for the status code, as shown in the preceding code. If the URL template starts with `~` (tilde), the `~` is replaced by the app's `PathBase`. When specifying an endpoint in the app, create an MVC view or Razor page for the endpoint.

This method is commonly used when the app:

- Should redirect the client to a different endpoint, usually in cases where a different app processes the error. For web apps, the client's browser address bar reflects the redirected endpoint.
- Shouldn't preserve and return the original status code with the initial redirect response.

### UseStatusCodePagesWithReExecute

The [UseStatusCodePagesWithReExecute](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithreexecute) extension method:

- Generates the response body by re-executing the request pipeline using an alternate path.
- Does not alter the status code before or after re-executing the pipeline.

The new pipeline execution may alter the response's status code, as the new pipeline has full control of the status code. If the new pipeline does not alter the status code, the original status code will be sent to the client.

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePagesWithReExecute("/StatusCode/{0}");
```

If an endpoint within the app is specified, create an MVC view or Razor page for the endpoint.

This method is commonly used when the app should:

- Process the request without redirecting to a different endpoint. For web apps, the client's browser address bar reflects the originally requested endpoint.
- Preserve and return the original status code with the response.

The URL template must start with `/` and may include a placeholder `{0}` for the status code. To pass the status code as a query-string parameter, pass a second argument into `UseStatusCodePagesWithReExecute`. For example:

```
var app = builder.Build();  
app.UseStatusCodePagesWithReExecute("/StatusCode", "?statusCode={0}");
```

The endpoint that processes the error can get the original URL that generated the error, as shown in the following example:

```
[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
public class StatusCodeModel : PageModel
{
    public int OriginalStatusCode { get; set; }

    public string? OriginalPathAndQuery { get; set; }

    public void OnGet(int statusCode)
    {
        OriginalStatusCode = statusCode;

        var statusCodeReExecuteFeature =
            HttpContext.Features.Get<IStatusCodeReExecuteFeature>();

        if (statusCodeReExecuteFeature is not null)
        {
            OriginalPathAndQuery = $"{statusCodeReExecuteFeature.OriginalPathBase}"
                                    + $"{statusCodeReExecuteFeature.OriginalPath}"
                                    + $"{statusCodeReExecuteFeature.OriginalQueryString}";

        }
    }
}
```

Since this middleware can re-execute the request pipeline:

- Middlewares need to handle reentrancy with the same request. This normally means either cleaning up their state after calling `_next` or caching their processing on the `HttpContext` to avoid redoing it. When dealing with the request body, this either means buffering or caching the results like the Form reader.
- Scoped services remain the same.

## Disable status code pages

To disable status code pages for an MVC controller or action method, use the [[SkipStatusCodePages]](/en-us/dotnet/api/microsoft.aspnetcore.mvc.skipstatuscodepagesattribute) attribute.

To disable status code pages for specific requests in a Razor Pages handler method or in an MVC controller, use [IStatusCodePagesFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.istatuscodepagesfeature):

```
public void OnGet()
{
    var statusCodePagesFeature =
        HttpContext.Features.Get<IStatusCodePagesFeature>();

    if (statusCodePagesFeature is not null)
    {
        statusCodePagesFeature.Enabled = false;
    }
}
```

## Exception-handling code

Code in exception handling pages can also throw exceptions. Production error pages should be tested thoroughly and take extra care to avoid throwing exceptions of their own.

### Response headers

Once the headers for a response are sent:

- The app can't change the response's status code.
- Any exception pages or handlers can't run. The response must be completed or the connection aborted.

## Server exception handling

In addition to the exception handling logic in an app, the [HTTP server implementation](servers/?view=aspnetcore-10.0) can handle some exceptions. If the server catches an exception before response headers are sent, the server sends a `500 - Internal Server Error` response without a response body. If the server catches an exception after response headers are sent, the server closes the connection. Requests that aren't handled by the app are handled by the server. Any exception that occurs when the server is handling the request is handled by the server's exception handling. The app's custom error pages, exception handling middleware, and filters don't affect this behavior.

## Startup exception handling

Only the hosting layer can handle exceptions that take place during app startup. The host can be configured to [capture startup errors](host/web-host?view=aspnetcore-10.0#capture-startup-errors) and [capture detailed errors](host/web-host?view=aspnetcore-10.0#detailed-errors).

The hosting layer can show an error page for a captured startup error only if the error occurs after host address/port binding. If binding fails:

- The hosting layer logs a critical exception.
- The dotnet process crashes.
- No error page is displayed when the HTTP server is [Kestrel](servers/kestrel?view=aspnetcore-10.0).

When running on [IIS](/en-us/iis) (or Azure App Service) or [IIS Express](/en-us/iis/extensions/introduction-to-iis-express/iis-express-overview), a *502.5 - Process Failure* is returned by the [ASP.NET Core Module](../host-and-deploy/aspnet-core-module?view=aspnetcore-10.0) if the process can't start. For more information, see [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0).

## Database error page

The Database developer page exception filter [AddDatabaseDeveloperPageExceptionFilter](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.databasedeveloperpageexceptionfilterserviceextensions.adddatabasedeveloperpageexceptionfilter) captures database-related exceptions that can be resolved by using Entity Framework Core migrations. When these exceptions occur, an HTML response is generated with details of possible actions to resolve the issue. This page is enabled only in the `Development` environment. The following code adds the Database developer page exception filter:

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDatabaseDeveloperPageExceptionFilter();
builder.Services.AddRazorPages();
```

## Exception filters

In MVC apps, exception filters can be configured globally or on a per-controller or per-action basis. In Razor Pages apps, they can be configured globally or per page model. These filters handle any unhandled exceptions that occur during the execution of a controller action or another filter. For more information, see [Filters in ASP.NET Core](../mvc/controllers/filters?view=aspnetcore-10.0#exception-filters).

Exception filters are useful for trapping exceptions that occur within MVC actions, but they're not as flexible as the built-in [exception handling middleware](https://github.com/dotnet/aspnetcore/blob/main/src/Middleware/Diagnostics/src/ExceptionHandler/ExceptionHandlerMiddleware.cs), [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). We recommend using `UseExceptionHandler`, unless you need to perform error handling differently based on which MVC action is chosen.

## Model state errors

For information about how to handle model state errors, see [Model binding](../mvc/models/model-binding?view=aspnetcore-10.0) and [Model validation](../mvc/models/validation?view=aspnetcore-10.0).

## Problem details

[Problem Details](https://www.rfc-editor.org/rfc/rfc7807.html) are not the only response format to describe an HTTP API error, however, they are commonly used to report errors for HTTP APIs.

The problem details service implements the [IProblemDetailsService](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice) interface, which supports creating problem details in ASP.NET Core. The [AddProblemDetails(IServiceCollection)](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.problemdetailsservicecollectionextensions.addproblemdetails#microsoft-extensions-dependencyinjection-problemdetailsservicecollectionextensions-addproblemdetails(microsoft-extensions-dependencyinjection-iservicecollection)) extension method on [IServiceCollection](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.iservicecollection) registers the default `IProblemDetailsService` implementation.

In ASP.NET Core apps, the following middleware generates problem details HTTP responses when `AddProblemDetails` is called, except when the [`Accept` request HTTP header](https://developer.mozilla.org/docs/Web/HTTP/Headers/Accept) doesn't include one of the content types supported by the registered [IProblemDetailsWriter](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailswriter) (default: `application/json`):

- [ExceptionHandlerMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.exceptionhandlermiddleware): Generates a problem details response when a custom handler is not defined.
- [StatusCodePagesMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.statuscodepagesmiddleware): Generates a problem details response by default.
- [DeveloperExceptionPageMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.developerexceptionpagemiddleware): Generates a problem details response in development when the `Accept` request HTTP header doesn't include `text/html`.

The following code configures the app to generate a problem details response for all HTTP client and server error responses that ***don't have a body content yet***:

```
builder.Services.AddProblemDetails();

var app = builder.Build();        

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler();
    app.UseHsts();
}

app.UseStatusCodePages();
```

The next section shows how to customize the problem details response body.

### Customize problem details

The automatic creation of a `ProblemDetails` can be customized using any of the following options:

1. Use [`ProblemDetailsOptions.CustomizeProblemDetails`](#customizeproblemdetails-operation)
2. Use a custom [`IProblemDetailsWriter`](#custom-iproblemdetailswriter)
3. Call the [`IProblemDetailsService` in a middleware](#problem-details-from-middleware)

#### `CustomizeProblemDetails` operation

The generated problem details can be customized using [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails), and the customizations are applied to all auto-generated problem details.

The following code uses [ProblemDetailsOptions](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions) to set [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails):

```
builder.Services.AddProblemDetails(options =>
    options.CustomizeProblemDetails = ctx =>
            ctx.ProblemDetails.Extensions.Add("nodeId", Environment.MachineName));

var app = builder.Build();        

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler();
    app.UseHsts();
}

app.UseStatusCodePages();
```

For example, an [`HTTP Status 400 Bad Request`](https://developer.mozilla.org/docs/Web/HTTP/Status/400) endpoint result produces the following problem details response body:

```
{
  "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
  "title": "Bad Request",
  "status": 400,
  "nodeId": "my-machine-name"
}
```

#### Custom `IProblemDetailsWriter`

An [IProblemDetailsWriter](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailswriter) implementation can be created for advanced customizations.

```
public class SampleProblemDetailsWriter : IProblemDetailsWriter
{
    // Indicates that only responses with StatusCode == 400
    // are handled by this writer. All others are
    // handled by different registered writers if available.
    public bool CanWrite(ProblemDetailsContext context)
        => context.HttpContext.Response.StatusCode == 400;

    public ValueTask WriteAsync(ProblemDetailsContext context)
    {
        // Additional customizations.

        // Write to the response.
        var response = context.HttpContext.Response;
        return new ValueTask(response.WriteAsJsonAsync(context.ProblemDetails));
    }
}
```

***Note:*** When using a custom `IProblemDetailsWriter`, the custom `IProblemDetailsWriter` must be registered before calling [AddRazorPages](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addrazorpages), [AddControllers](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addcontrollers), [AddControllersWithViews](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addcontrollerswithviews), or [AddMvc](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.mvcservicecollectionextensions.addmvc):

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddTransient<IProblemDetailsWriter, SampleProblemDetailsWriter>();

var app = builder.Build();

// Middleware to handle writing problem details to the response.
app.Use(async (context, next) =>
{
    await next(context);
    var mathErrorFeature = context.Features.Get<MathErrorFeature>();
    if (mathErrorFeature is not null)
    {
        if (context.RequestServices.GetService<IProblemDetailsWriter>() is
            { } problemDetailsService)
        {

            if (problemDetailsService.CanWrite(new ProblemDetailsContext() { HttpContext = context }))
            {
                (string Detail, string Type) details = mathErrorFeature.MathError switch
                {
                    MathErrorType.DivisionByZeroError => ("Divison by zero is not defined.",
                        "https://en.wikipedia.org/wiki/Division_by_zero"),
                    _ => ("Negative or complex numbers are not valid input.",
                        "https://en.wikipedia.org/wiki/Square_root")
                };

                await problemDetailsService.WriteAsync(new ProblemDetailsContext
                {
                    HttpContext = context,
                    ProblemDetails =
                    {
                        Title = "Bad Input",
                        Detail = details.Detail,
                        Type = details.Type
                    }
                });
            }
        }
    }
});

// /divide?numerator=2&denominator=4
app.MapGet("/divide", (HttpContext context, double numerator, double denominator) =>
{
    if (denominator == 0)
    {
        var errorType = new MathErrorFeature
        {
            MathError = MathErrorType.DivisionByZeroError
        };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(numerator / denominator);
});

// /squareroot?radicand=16
app.MapGet("/squareroot", (HttpContext context, double radicand) =>
{
    if (radicand < 0)
    {
        var errorType = new MathErrorFeature
        {
            MathError = MathErrorType.NegativeRadicandError
        };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(Math.Sqrt(radicand));
});

app.Run();
```

#### Problem details from Middleware

An alternative approach to using [ProblemDetailsOptions](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions) with [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails) is to set the [ProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailscontext.problemdetails#microsoft-aspnetcore-http-problemdetailscontext-problemdetails) in middleware. A problem details response can be written by calling [`IProblemDetailsService.WriteAsync`](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice.writeasync?view=aspnetcore-7.0&preserve-view=true):

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseHttpsRedirection();
app.UseStatusCodePages();

// Middleware to handle writing problem details to the response.
app.Use(async (context, next) =>
{
    await next(context);
    var mathErrorFeature = context.Features.Get<MathErrorFeature>();
    if (mathErrorFeature is not null)
    {
        if (context.RequestServices.GetService<IProblemDetailsService>() is
                                                           { } problemDetailsService)
        {
            (string Detail, string Type) details = mathErrorFeature.MathError switch
            {
                MathErrorType.DivisionByZeroError => ("Divison by zero is not defined.",
                "https://en.wikipedia.org/wiki/Division_by_zero"),
                _ => ("Negative or complex numbers are not valid input.", 
                "https://en.wikipedia.org/wiki/Square_root")
            };

            await problemDetailsService.WriteAsync(new ProblemDetailsContext
            {
                HttpContext = context,
                ProblemDetails =
                {
                    Title = "Bad Input",
                    Detail = details.Detail,
                    Type = details.Type
                }
            });
        }
    }
});

// /divide?numerator=2&denominator=4
app.MapGet("/divide", (HttpContext context, double numerator, double denominator) =>
{
    if (denominator == 0)
    {
        var errorType = new MathErrorFeature { MathError =
                                               MathErrorType.DivisionByZeroError };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(numerator / denominator);
});

// /squareroot?radicand=16
app.MapGet("/squareroot", (HttpContext context, double radicand) =>
{
    if (radicand < 0)
    {
        var errorType = new MathErrorFeature { MathError =
                                               MathErrorType.NegativeRadicandError };
        context.Features.Set(errorType);
        return Results.BadRequest();
    }

    return Results.Ok(Math.Sqrt(radicand));
});

app.MapControllers();

app.Run();
```

In the preceding code, the Minimal API endpoints `/divide` and `/squareroot` return the expected custom problem response on error input.

The API controller endpoints return the default problem response on error input, not the custom problem response. The default problem response is returned because the API controller has written to the response stream, [Problem details for error status codes](/en-us/aspnet/core/web-api/#problem-details-for-error-status-codes-1), before [`IProblemDetailsService.WriteAsync`](https://github.com/dotnet/aspnetcore/blob/ce2db7ea0b161fc5eb35710fca6feeafeeac37bc/src/Http/Http.Extensions/src/ProblemDetailsService.cs#L24) is called and the response is **not** written again.

The following `ValuesController` returns [BadRequestResult](/en-us/dotnet/api/microsoft.aspnetcore.mvc.badrequestresult), which writes to the response stream and therefore prevents the custom problem response from being returned.

```
[Route("api/[controller]/[action]")]
[ApiController]
public class ValuesController : ControllerBase
{
    // /api/values/divide/1/2
    [HttpGet("{Numerator}/{Denominator}")]
    public IActionResult Divide(double Numerator, double Denominator)
    {
        if (Denominator == 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.DivisionByZeroError
            };
            HttpContext.Features.Set(errorType);
            return BadRequest();
        }

        return Ok(Numerator / Denominator);
    }

    // /api/values/squareroot/4
    [HttpGet("{radicand}")]
    public IActionResult Squareroot(double radicand)
    {
        if (radicand < 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.NegativeRadicandError
            };
            HttpContext.Features.Set(errorType);
            return BadRequest();
        }

        return Ok(Math.Sqrt(radicand));
    }

}
```

The following `Values3Controller` returns [`ControllerBase.Problem`](/en-us/dotnet/api/microsoft.aspnetcore.mvc.controllerbase.problem) so the expected custom problem result is returned:

```
[Route("api/[controller]/[action]")]
[ApiController]
public class Values3Controller : ControllerBase
{
    // /api/values3/divide/1/2
    [HttpGet("{Numerator}/{Denominator}")]
    public IActionResult Divide(double Numerator, double Denominator)
    {
        if (Denominator == 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.DivisionByZeroError
            };
            HttpContext.Features.Set(errorType);
            return Problem(
                title: "Bad Input",
                detail: "Divison by zero is not defined.",
                type: "https://en.wikipedia.org/wiki/Division_by_zero",
                statusCode: StatusCodes.Status400BadRequest
                );
        }

        return Ok(Numerator / Denominator);
    }

    // /api/values3/squareroot/4
    [HttpGet("{radicand}")]
    public IActionResult Squareroot(double radicand)
    {
        if (radicand < 0)
        {
            var errorType = new MathErrorFeature
            {
                MathError = MathErrorType.NegativeRadicandError
            };
            HttpContext.Features.Set(errorType);
            return Problem(
                title: "Bad Input",
                detail: "Negative or complex numbers are not valid input.",
                type: "https://en.wikipedia.org/wiki/Square_root",
                statusCode: StatusCodes.Status400BadRequest
                );
        }

        return Ok(Math.Sqrt(radicand));
    }

}
```

## Produce a ProblemDetails payload for exceptions

Consider the following app:

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}

app.MapControllers();
app.Run();
```

In non-development environments, when an exception occurs, the following is a standard [ProblemDetails response](https://datatracker.ietf.org/doc/html/rfc7807) that is returned to the client:

```
{
"type":"https://tools.ietf.org/html/rfc7231#section-6.6.1",
"title":"An error occurred while processing your request.",
"status":500,"traceId":"00-b644<snip>-00"
}
```

For most apps, the preceding code is all that's needed for exceptions. However, the following section shows how to get more detailed problem responses.

An alternative to a [custom exception handler page](error-handling?view=aspnetcore-10.0#exception-handler-page) is to provide a lambda to [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). Using a lambda allows access to the error and writing a problem details response with [`IProblemDetailsService.WriteAsync`](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice.writeasync?view=aspnetcore-7.0&preserve-view=true):

```
using Microsoft.AspNetCore.Diagnostics;
using static System.Net.Mime.MediaTypeNames;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}
else
{
    app.UseExceptionHandler(exceptionHandlerApp =>
    {
        exceptionHandlerApp.Run(async context =>
        {
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;
            context.Response.ContentType = Text.Plain;

            var title = "Bad Input";
            var detail = "Invalid input";
            var type = "https://errors.example.com/badInput";

            if (context.RequestServices.GetService<IProblemDetailsService>() is
                { } problemDetailsService)
            {
                var exceptionHandlerFeature =
               context.Features.Get<IExceptionHandlerFeature>();

                var exceptionType = exceptionHandlerFeature?.Error;
                if (exceptionType != null &&
                   exceptionType.Message.Contains("infinity"))
                {
                    title = "Argument exception";
                    detail = "Invalid input";
                    type = "https://errors.example.com/argumentException";
                }

                await problemDetailsService.WriteAsync(new ProblemDetailsContext
                {
                    HttpContext = context,
                    ProblemDetails =
                {
                    Title = title,
                    Detail = detail,
                    Type = type
                }
                });
            }
        });
    });
}

app.MapControllers();
app.Run();
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

An alternative approach to generate problem details is to use the third-party NuGet package [Hellang.Middleware.ProblemDetails](https://www.nuget.org/packages/Hellang.Middleware.ProblemDetails/) that can be used to map exceptions and client errors to problem details.

## Additional resources

- [View or download sample code](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples) ([how to download](./?view=aspnetcore-10.0#how-to-download-a-sample))
- [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0)
- [Common error troubleshooting for Azure App Service and IIS with ASP.NET Core](../host-and-deploy/azure-iis-errors-reference?view=aspnetcore-10.0)

By [Tom Dykstra](https://github.com/tdykstra/)

This article covers common approaches to handling errors in ASP.NET Core web apps. See [Handle errors in ASP.NET Core APIs](error-handling-api?view=aspnetcore-10.0) for web APIs.

## Developer exception page

The *Developer Exception Page* displays detailed information about unhandled request exceptions. ASP.NET Core apps enable the developer exception page by default when both:

- Running in the [`Development` environment](environments?view=aspnetcore-10.0).
- App created with the current templates, that is, using [WebApplication.CreateBuilder](/en-us/dotnet/api/microsoft.aspnetcore.builder.webapplication.createbuilder). Apps created using the [`WebHost.CreateDefaultBuilder`](/en-us/dotnet/api/microsoft.aspnetcore.webhost.createdefaultbuilder#microsoft-aspnetcore-webhost-createdefaultbuilder) must enable the developer exception page by calling `app.UseDeveloperExceptionPage` in `Configure`.

The developer exception page runs early in the middleware pipeline, so that it can catch unhandled exceptions thrown in middleware that follows.

Detailed exception information shouldn't be displayed publicly when the app runs in the `Production` environment. For more information on configuring environments, see [ASP.NET Core runtime environments](environments?view=aspnetcore-10.0).

The Developer Exception Page can include the following information about the exception and the request:

- Stack trace
- Query string parameters, if any
- Cookies, if any
- Headers

The Developer Exception Page isn't guaranteed to provide any information. Use [Logging](logging/?view=aspnetcore-10.0) for complete error information.

## Exception handler page

To configure a custom error handling page for the [`Production` environment](environments?view=aspnetcore-10.0), call [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). This exception handling middleware:

- Catches and logs unhandled exceptions.
- Re-executes the request in an alternate pipeline using the path indicated. The request isn't re-executed if the response has started. The template-generated code re-executes the request using the `/Error` path.

Warning

If the alternate pipeline throws an exception of its own, exception handling middleware rethrows the original exception.

In the following example, [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler) adds the exception handling middleware in non-`Development` environments:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}
```

The Razor Pages app template provides an Error page (`.cshtml`) and [PageModel](/en-us/dotnet/api/microsoft.aspnetcore.mvc.razorpages.pagemodel) class (`ErrorModel`) in the *Pages* folder. For an MVC app, the project template includes an `Error` action method and an Error view for the Home controller.

The exception handling middleware re-executes the request using the *original* HTTP method. If an error handler endpoint is restricted to a specific set of HTTP methods, it runs only for those HTTP methods. For example, an MVC controller action that uses the `[HttpGet]` attribute runs only for GET requests. To ensure that *all* requests reach the custom error handling page, don't restrict them to a specific set of HTTP methods.

To handle exceptions differently based on the original HTTP method:

- For Razor Pages, create multiple handler methods. For example, use `OnGet` to handle GET exceptions and use `OnPost` to handle POST exceptions.
- For MVC, apply HTTP verb attributes to multiple actions. For example, use `[HttpGet]` to handle GET exceptions and use `[HttpPost]` to handle POST exceptions.

To allow unauthenticated users to view the custom error handling page, ensure that it supports anonymous access.

### Access the exception

Use [IExceptionHandlerPathFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandlerpathfeature) to access the exception and the original request path in an error handler. The following example uses `IExceptionHandlerPathFeature` to get more information about the exception that was thrown:

```
[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
[IgnoreAntiforgeryToken]
public class ErrorModel : PageModel
{
    public string? RequestId { get; set; }

    public bool ShowRequestId => !string.IsNullOrEmpty(RequestId);

    public string? ExceptionMessage { get; set; }

    public void OnGet()
    {
        RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;

        var exceptionHandlerPathFeature =
            HttpContext.Features.Get<IExceptionHandlerPathFeature>();

        if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
        {
            ExceptionMessage = "The file was not found.";
        }

        if (exceptionHandlerPathFeature?.Path == "/")
        {
            ExceptionMessage ??= string.Empty;
            ExceptionMessage += " Page: Home.";
        }
    }
}
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

## Exception handler lambda

An alternative to a [custom exception handler page](#exception-handler-page) is to provide a lambda to [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). Using a lambda allows access to the error before returning the response.

The following code uses a lambda for exception handling:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler(exceptionHandlerApp =>
    {
        exceptionHandlerApp.Run(async context =>
        {
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;

            // using static System.Net.Mime.MediaTypeNames;
            context.Response.ContentType = Text.Plain;

            await context.Response.WriteAsync("An exception was thrown.");

            var exceptionHandlerPathFeature =
                context.Features.Get<IExceptionHandlerPathFeature>();

            if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
            {
                await context.Response.WriteAsync(" The file was not found.");
            }

            if (exceptionHandlerPathFeature?.Path == "/")
            {
                await context.Response.WriteAsync(" Page: Home.");
            }
        });
    });

    app.UseHsts();
}
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

## UseStatusCodePages

By default, an ASP.NET Core app doesn't provide a status code page for HTTP error status codes, such as *404 - Not Found*. When the app sets an HTTP 400-599 error status code that doesn't have a body, it returns the status code and an empty response body. To enable default text-only handlers for common error status codes, call [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) in `Program.cs`:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePages();
```

Call `UseStatusCodePages` before request handling middleware. For example, call `UseStatusCodePages` before the static file middleware and the endpoints middleware.

When `UseStatusCodePages` isn't used, navigating to a URL without an endpoint returns a browser-dependent error message indicating the endpoint can't be found. When `UseStatusCodePages` is called, the browser returns the following response:

```
Status Code: 404; Not Found
```

`UseStatusCodePages` isn't typically used in production because it returns a message that isn't useful to users.

Note

The status code pages middleware does **not** catch exceptions. To provide a custom error handling page, use the [exception handler page](#exception-handler-page).

### UseStatusCodePages with format string

To customize the response content type and text, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a content type and format string:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

// using static System.Net.Mime.MediaTypeNames;
app.UseStatusCodePages(Text.Plain, "Status Code Page: {0}");
```

In the preceding code, `{0}` is a placeholder for the error code.

`UseStatusCodePages` with a format string isn't typically used in production because it returns a message that isn't useful to users.

### UseStatusCodePages with lambda

To specify custom error-handling and response-writing code, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a lambda expression:

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePages(async statusCodeContext =>
{
    // using static System.Net.Mime.MediaTypeNames;
    statusCodeContext.HttpContext.Response.ContentType = Text.Plain;

    await statusCodeContext.HttpContext.Response.WriteAsync(
        $"Status Code Page: {statusCodeContext.HttpContext.Response.StatusCode}");
});
```

`UseStatusCodePages` with a lambda isn't typically used in production because it returns a message that isn't useful to users.

### UseStatusCodePagesWithRedirects

The [UseStatusCodePagesWithRedirects](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithredirects) extension method:

- Sends a [302 - Found](https://developer.mozilla.org/docs/Web/HTTP/Status/302) status code to the client.
- Redirects the client to the error handling endpoint provided in the URL template. The error handling endpoint typically displays error information and returns HTTP 200.

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePagesWithRedirects("/StatusCode/{0}");
```

The URL template can include a `{0}` placeholder for the status code, as shown in the preceding code. If the URL template starts with `~` (tilde), the `~` is replaced by the app's `PathBase`. When specifying an endpoint in the app, create an MVC view or Razor page for the endpoint.

This method is commonly used when the app:

- Should redirect the client to a different endpoint, usually in cases where a different app processes the error. For web apps, the client's browser address bar reflects the redirected endpoint.
- Shouldn't preserve and return the original status code with the initial redirect response.

### UseStatusCodePagesWithReExecute

The [UseStatusCodePagesWithReExecute](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithreexecute) extension method:

- Returns the original status code to the client.
- Generates the response body by re-executing the request pipeline using an alternate path.

```
var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStatusCodePagesWithReExecute("/StatusCode/{0}");
```

If an endpoint within the app is specified, create an MVC view or Razor page for the endpoint.

This method is commonly used when the app should:

- Process the request without redirecting to a different endpoint. For web apps, the client's browser address bar reflects the originally requested endpoint.
- Preserve and return the original status code with the response.

The URL template must start with `/` and may include a placeholder `{0}` for the status code. To pass the status code as a query-string parameter, pass a second argument into `UseStatusCodePagesWithReExecute`. For example:

```
app.UseStatusCodePagesWithReExecute("/StatusCode", "?statusCode={0}");
```

The endpoint that processes the error can get the original URL that generated the error, as shown in the following example:

```
[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
public class StatusCodeModel : PageModel
{
    public int OriginalStatusCode { get; set; }

    public string? OriginalPathAndQuery { get; set; }

    public void OnGet(int statusCode)
    {
        OriginalStatusCode = statusCode;

        var statusCodeReExecuteFeature =
            HttpContext.Features.Get<IStatusCodeReExecuteFeature>();

        if (statusCodeReExecuteFeature is not null)
        {
            OriginalPathAndQuery = string.Join(
                statusCodeReExecuteFeature.OriginalPathBase,
                statusCodeReExecuteFeature.OriginalPath,
                statusCodeReExecuteFeature.OriginalQueryString);
        }
    }
}
```

## Disable status code pages

To disable status code pages for an MVC controller or action method, use the [[SkipStatusCodePages]](/en-us/dotnet/api/microsoft.aspnetcore.mvc.skipstatuscodepagesattribute) attribute.

To disable status code pages for specific requests in a Razor Pages handler method or in an MVC controller, use [IStatusCodePagesFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.istatuscodepagesfeature):

```
public void OnGet()
{
    var statusCodePagesFeature =
        HttpContext.Features.Get<IStatusCodePagesFeature>();

    if (statusCodePagesFeature is not null)
    {
        statusCodePagesFeature.Enabled = false;
    }
}
```

## Exception-handling code

Code in exception handling pages can also throw exceptions. Production error pages should be tested thoroughly and take extra care to avoid throwing exceptions of their own.

### Response headers

Once the headers for a response are sent:

- The app can't change the response's status code.
- Any exception pages or handlers can't run. The response must be completed or the connection aborted.

## Server exception handling

In addition to the exception handling logic in an app, the [HTTP server implementation](servers/?view=aspnetcore-10.0) can handle some exceptions. If the server catches an exception before response headers are sent, the server sends a `500 - Internal Server Error` response without a response body. If the server catches an exception after response headers are sent, the server closes the connection. Requests that aren't handled by the app are handled by the server. Any exception that occurs when the server is handling the request is handled by the server's exception handling. The app's custom error pages, exception handling middleware, and filters don't affect this behavior.

## Startup exception handling

Only the hosting layer can handle exceptions that take place during app startup. The host can be configured to [capture startup errors](host/web-host?view=aspnetcore-10.0#capture-startup-errors) and [capture detailed errors](host/web-host?view=aspnetcore-10.0#detailed-errors).

The hosting layer can show an error page for a captured startup error only if the error occurs after host address/port binding. If binding fails:

- The hosting layer logs a critical exception.
- The dotnet process crashes.
- No error page is displayed when the HTTP server is [Kestrel](servers/kestrel?view=aspnetcore-10.0).

When running on [IIS](/en-us/iis) (or Azure App Service) or [IIS Express](/en-us/iis/extensions/introduction-to-iis-express/iis-express-overview), a *502.5 - Process Failure* is returned by the [ASP.NET Core Module](../host-and-deploy/aspnet-core-module?view=aspnetcore-10.0) if the process can't start. For more information, see [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0).

## Database error page

The Database developer page exception filter [AddDatabaseDeveloperPageExceptionFilter](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.databasedeveloperpageexceptionfilterserviceextensions.adddatabasedeveloperpageexceptionfilter) captures database-related exceptions that can be resolved by using Entity Framework Core migrations. When these exceptions occur, an HTML response is generated with details of possible actions to resolve the issue. This page is enabled only in the `Development` environment. The following code adds the Database developer page exception filter:

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDatabaseDeveloperPageExceptionFilter();
builder.Services.AddRazorPages();
```

## Exception filters

In MVC apps, exception filters can be configured globally or on a per-controller or per-action basis. In Razor Pages apps, they can be configured globally or per page model. These filters handle any unhandled exceptions that occur during the execution of a controller action or another filter. For more information, see [Filters in ASP.NET Core](../mvc/controllers/filters?view=aspnetcore-10.0#exception-filters).

Exception filters are useful for trapping exceptions that occur within MVC actions, but they're not as flexible as the built-in [exception handling middleware](https://github.com/dotnet/aspnetcore/blob/main/src/Middleware/Diagnostics/src/ExceptionHandler/ExceptionHandlerMiddleware.cs), [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). We recommend using `UseExceptionHandler`, unless you need to perform error handling differently based on which MVC action is chosen.

## Model state errors

For information about how to handle model state errors, see [Model binding](../mvc/models/model-binding?view=aspnetcore-10.0) and [Model validation](../mvc/models/validation?view=aspnetcore-10.0).

## Additional resources

- [View or download sample code](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples) ([how to download](./?view=aspnetcore-10.0#how-to-download-a-sample))
- [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0)
- [Common error troubleshooting for Azure App Service and IIS with ASP.NET Core](../host-and-deploy/azure-iis-errors-reference?view=aspnetcore-10.0)

By [Kirk Larkin](https://twitter.com/serpent5), [Tom Dykstra](https://github.com/tdykstra/), and [Steve Smith](https://ardalis.com/)

This article covers common approaches to handling errors in ASP.NET Core web apps. See [Handle errors in ASP.NET Core APIs](error-handling-api?view=aspnetcore-10.0) for web APIs.

[View or download sample code](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples). ([How to download](./?view=aspnetcore-10.0#how-to-download-a-sample).) The network tab on the F12 browser developer tools is useful when testing the sample app.

## Developer Exception Page

The *Developer Exception Page* displays detailed information about unhandled request exceptions. The ASP.NET Core templates generate the following code:

```
public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
{
    if (env.IsDevelopment())
    {
        app.UseDeveloperExceptionPage();
    }
    else
    {
        app.UseExceptionHandler("/Error");
        app.UseHsts();
    }

    app.UseHttpsRedirection();
    app.UseStaticFiles();

    app.UseRouting();

    app.UseAuthorization();

    app.UseEndpoints(endpoints =>
    {
        endpoints.MapRazorPages();
    });
}
```

The preceding highlighted code enables the developer exception page when the app is running in the [`Development` environment](environments?view=aspnetcore-10.0).

The templates place [UseDeveloperExceptionPage](/en-us/dotnet/api/microsoft.aspnetcore.builder.developerexceptionpageextensions.usedeveloperexceptionpage) early in the middleware pipeline so that it can catch unhandled exceptions thrown in middleware that follows.

The preceding code enables the Developer Exception Page ***only*** when the app runs in the `Development` environment. Detailed exception information shouldn't be displayed publicly when the app runs in the `Production` environment. For more information on configuring environments, see [ASP.NET Core runtime environments](environments?view=aspnetcore-10.0).

The Developer Exception Page can include the following information about the exception and the request:

- Stack trace
- Query string parameters if any
- Cookies if any
- Headers

The Developer Exception Page isn't guaranteed to provide any information. Use [Logging](logging/?view=aspnetcore-10.0) for complete error information.

## Exception handler page

To configure a custom error handling page for the [`Production` environment](environments?view=aspnetcore-10.0), call [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). This exception handling middleware:

- Catches and logs unhandled exceptions.
- Re-executes the request in an alternate pipeline using the path indicated. The request isn't re-executed if the response has started. The template-generated code re-executes the request using the `/Error` path.

Warning

If the alternate pipeline throws an exception of its own, exception handling middleware rethrows the original exception.

In the following example, [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler) adds the exception handling middleware in non-`Development` environments:

```
if (env.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}
else
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}
```

The Razor Pages app template provides an Error page (`.cshtml`) and [PageModel](/en-us/dotnet/api/microsoft.aspnetcore.mvc.razorpages.pagemodel) class (`ErrorModel`) in the *Pages* folder. For an MVC app, the project template includes an `Error` action method and an Error view for the Home controller.

The exception handling middleware re-executes the request using the *original* HTTP method. If an error handler endpoint is restricted to a specific set of HTTP methods, it runs only for those HTTP methods. For example, an MVC controller action that uses the `[HttpGet]` attribute runs only for GET requests. To ensure that *all* requests reach the custom error handling page, don't restrict them to a specific set of HTTP methods.

To handle exceptions differently based on the original HTTP method:

- For Razor Pages, create multiple handler methods. For example, use `OnGet` to handle GET exceptions and use `OnPost` to handle POST exceptions.
- For MVC, apply HTTP verb attributes to multiple actions. For example, use `[HttpGet]` to handle GET exceptions and use `[HttpPost]` to handle POST exceptions.

To allow unauthenticated users to view the custom error handling page, ensure that it supports anonymous access.

### Access the exception

Use [IExceptionHandlerPathFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandlerpathfeature) to access the exception and the original request path in an error handler. The following code adds `ExceptionMessage` to the default `Pages/Error.cshtml.cs` generated by the ASP.NET Core templates:

```
[ResponseCache(Duration=0, Location=ResponseCacheLocation.None, NoStore=true)]
[IgnoreAntiforgeryToken]
public class ErrorModel : PageModel
{
    public string RequestId { get; set; }
    public bool ShowRequestId => !string.IsNullOrEmpty(RequestId);
    public string ExceptionMessage { get; set; }
    private readonly ILogger<ErrorModel> _logger;

    public ErrorModel(ILogger<ErrorModel> logger)
    {
        _logger = logger;
    }

    public void OnGet()
    {
        RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;

        var exceptionHandlerPathFeature =
        HttpContext.Features.Get<IExceptionHandlerPathFeature>();
        if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
        {
            ExceptionMessage = "File error thrown";
            _logger.LogError(ExceptionMessage);
        }
        if (exceptionHandlerPathFeature?.Path == "/index")
        {
            ExceptionMessage += " from home page";
        }
    }
}
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

To test the exception in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x):

- Set the environment to production.
- Remove the comments from `webBuilder.UseStartup<Startup>();` in `Program.cs`.
- Select **Trigger an exception** on the home page.

## Exception handler lambda

An alternative to a [custom exception handler page](#exception-handler-page) is to provide a lambda to [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). Using a lambda allows access to the error before returning the response.

The following code uses a lambda for exception handling:

```
public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
{
    if (env.IsDevelopment())
    {
        app.UseDeveloperExceptionPage();
    }
    else
    {
        app.UseExceptionHandler(errorApp =>
        {
            errorApp.Run(async context =>
            {
                context.Response.StatusCode = (int) HttpStatusCode.InternalServerError;;
                context.Response.ContentType = "text/html";

                await context.Response.WriteAsync("<html lang=\"en\"><body>\r\n");
                await context.Response.WriteAsync("ERROR!<br><br>\r\n");

                var exceptionHandlerPathFeature =
                    context.Features.Get<IExceptionHandlerPathFeature>();

                if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
                {
                    await context.Response.WriteAsync(
                                              "File error thrown!<br><br>\r\n");
                }

                await context.Response.WriteAsync(
                                              "<a href=\"/\">Home</a><br>\r\n");
                await context.Response.WriteAsync("</body></html>\r\n");
                await context.Response.WriteAsync(new string(' ', 512)); 
            });
        });
        app.UseHsts();
    }

    app.UseHttpsRedirection();
    app.UseStaticFiles();

    app.UseRouting();

    app.UseAuthorization();

    app.UseEndpoints(endpoints =>
    {
        endpoints.MapRazorPages();
    });
}
```

Warning

Do **not** serve sensitive error information from [IExceptionHandlerFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandlerfeature) or [IExceptionHandlerPathFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandlerpathfeature) to clients. Serving errors is a security risk.

To test the exception handling lambda in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x):

- Set the environment to production.
- Remove the comments from `webBuilder.UseStartup<StartupLambda>();` in `Program.cs`.
- Select **Trigger an exception** on the home page.

## UseStatusCodePages

By default, an ASP.NET Core app doesn't provide a status code page for HTTP error status codes, such as *404 - Not Found*. When the app sets an HTTP 400-599 error status code that doesn't have a body, it returns the status code and an empty response body. To provide status code pages, use the status code pages middleware. To enable default text-only handlers for common error status codes, call [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) in the `Startup.Configure` method:

```
public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
{
    if (env.IsDevelopment())
    {
        app.UseDeveloperExceptionPage();
    }
    else
    {
        app.UseExceptionHandler("/Error");
        app.UseHsts();
    }

    app.UseStatusCodePages();

    app.UseHttpsRedirection();
    app.UseStaticFiles();

    app.UseRouting();

    app.UseAuthorization();

    app.UseEndpoints(endpoints =>
    {
        endpoints.MapRazorPages();
    });
}
```

Call `UseStatusCodePages` before request handling middleware. For example, call `UseStatusCodePages` before the static file middleware and the endpoints middleware.

When `UseStatusCodePages` isn't used, navigating to a URL without an endpoint returns a browser-dependent error message indicating the endpoint can't be found. For example, navigating to `Home/Privacy2`. When `UseStatusCodePages` is called, the browser returns:

```
Status Code: 404; Not Found
```

`UseStatusCodePages` isn't typically used in production because it returns a message that isn't useful to users.

To test `UseStatusCodePages` in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x):

- Set the environment to production.
- Remove the comments from `webBuilder.UseStartup<StartupUseStatusCodePages>();` in `Program.cs`.
- Select the links on the home page on the home page.

Note

The status code pages middleware does **not** catch exceptions. To provide a custom error handling page, use the [exception handler page](#exception-handler-page).

### UseStatusCodePages with format string

To customize the response content type and text, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a content type and format string:

```
public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
{
    if (env.IsDevelopment())
    {
        app.UseDeveloperExceptionPage();
    }
    else
    {
        app.UseExceptionHandler("/Error");
        app.UseHsts();
    }

    app.UseStatusCodePages(
        "text/plain", "Status code page, status code: {0}");

    app.UseHttpsRedirection();
    app.UseStaticFiles();

    app.UseRouting();

    app.UseAuthorization();

    app.UseEndpoints(endpoints =>
    {
        endpoints.MapRazorPages();
    });
}
```

In the preceding code, `{0}` is a placeholder for the error code.

`UseStatusCodePages` with a format string isn't typically used in production because it returns a message that isn't useful to users.

To test `UseStatusCodePages` in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x), remove the comments from `webBuilder.UseStartup<StartupFormat>();` in `Program.cs`.

### UseStatusCodePages with lambda

To specify custom error-handling and response-writing code, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a lambda expression:

```
public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
{
    if (env.IsDevelopment())
    {
        app.UseDeveloperExceptionPage();
    }
    else
    {
        app.UseExceptionHandler("/Error");
        app.UseHsts();
    }

    app.UseStatusCodePages(async context =>
    {
        context.HttpContext.Response.ContentType = "text/plain";

        await context.HttpContext.Response.WriteAsync(
            "Status code page, status code: " +
            context.HttpContext.Response.StatusCode);
    });

    app.UseHttpsRedirection();
    app.UseStaticFiles();

    app.UseRouting();

    app.UseAuthorization();

    app.UseEndpoints(endpoints =>
    {
        endpoints.MapRazorPages();
    });
}
```

`UseStatusCodePages` with a lambda isn't typically used in production because it returns a message that isn't useful to users.

To test `UseStatusCodePages` in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x), remove the comments from `webBuilder.UseStartup<StartupStatusLambda>();` in `Program.cs`.

### UseStatusCodePagesWithRedirects

The [UseStatusCodePagesWithRedirects](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithredirects) extension method:

- Sends a [302 - Found](https://developer.mozilla.org/docs/Web/HTTP/Status/302) status code to the client.
- Redirects the client to the error handling endpoint provided in the URL template. The error handling endpoint typically displays error information and returns HTTP 200.

```
public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
{
    if (env.IsDevelopment())
    {
        app.UseDeveloperExceptionPage();
    }
    else
    {
        app.UseExceptionHandler("/Error");
        app.UseHsts();
    }

    app.UseStatusCodePagesWithRedirects("/MyStatusCode?code={0}");

    app.UseHttpsRedirection();
    app.UseStaticFiles();

    app.UseRouting();

    app.UseAuthorization();

    app.UseEndpoints(endpoints =>
    {
        endpoints.MapRazorPages();
    });
}
```

The URL template can include a `{0}` placeholder for the status code, as shown in the preceding code. If the URL template starts with `~` (tilde), the `~` is replaced by the app's `PathBase`. When specifying an endpoint in the app, create an MVC view or Razor page for the endpoint. For a Razor Pages example, see [Pages/MyStatusCode.cshtml](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x/ErrorHandlingSample/Pages) in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x).

This method is commonly used when the app:

- Should redirect the client to a different endpoint, usually in cases where a different app processes the error. For web apps, the client's browser address bar reflects the redirected endpoint.
- Shouldn't preserve and return the original status code with the initial redirect response.

To test `UseStatusCodePages` in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x), remove the comments from `webBuilder.UseStartup<StartupSCredirect>();` in `Program.cs`.

### UseStatusCodePagesWithReExecute

The [UseStatusCodePagesWithReExecute](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithreexecute) extension method:

- Returns the original status code to the client.
- Generates the response body by re-executing the request pipeline using an alternate path.

```
public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
{
    if (env.IsDevelopment())
    {
        app.UseDeveloperExceptionPage();
    }
    else
    {
        app.UseExceptionHandler("/Error");
        app.UseHsts();
    }

    app.UseStatusCodePagesWithReExecute("/MyStatusCode2", "?code={0}");

    app.UseHttpsRedirection();
    app.UseStaticFiles();

    app.UseRouting();

    app.UseAuthorization();

    app.UseEndpoints(endpoints =>
    {
        endpoints.MapRazorPages();
    });
}
```

If an endpoint within the app is specified, create an MVC view or Razor page for the endpoint. Ensure `UseStatusCodePagesWithReExecute` is placed before `UseRouting` so the request can be rerouted to the status page. For a Razor Pages example, see [Pages/MyStatusCode2.cshtml](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x/ErrorHandlingSample/Pages) in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x).

This method is commonly used when the app should:

- Process the request without redirecting to a different endpoint. For web apps, the client's browser address bar reflects the originally requested endpoint.
- Preserve and return the original status code with the response.

The URL and query string templates may include a placeholder `{0}` for the status code. The URL template must start with `/`.

The endpoint that processes the error can get the original URL that generated the error, as shown in the following example:

```
[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
public class MyStatusCode2Model : PageModel
{
    public string RequestId { get; set; }
    public bool ShowRequestId => !string.IsNullOrEmpty(RequestId);

    public string ErrorStatusCode { get; set; }

    public string OriginalURL { get; set; }
    public bool ShowOriginalURL => !string.IsNullOrEmpty(OriginalURL);

    public void OnGet(string code)
    {
        RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;
        ErrorStatusCode = code;

        var statusCodeReExecuteFeature = HttpContext.Features.Get<
                                               IStatusCodeReExecuteFeature>();
        if (statusCodeReExecuteFeature != null)
        {
            OriginalURL =
                statusCodeReExecuteFeature.OriginalPathBase
                + statusCodeReExecuteFeature.OriginalPath
                + statusCodeReExecuteFeature.OriginalQueryString;
        }
    }
}
```

For a Razor Pages example, see [Pages/MyStatusCode2.cshtml](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x/ErrorHandlingSample/Pages) in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x).

To test `UseStatusCodePages` in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples/5.x), remove the comments from `webBuilder.UseStartup<StartupSCreX>();` in `Program.cs`.

## Disable status code pages

To disable status code pages for an MVC controller or action method, use the [[SkipStatusCodePages]](/en-us/dotnet/api/microsoft.aspnetcore.mvc.skipstatuscodepagesattribute) attribute.

To disable status code pages for specific requests in a Razor Pages handler method or in an MVC controller, use [IStatusCodePagesFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.istatuscodepagesfeature):

```
public void OnGet()
{
    // using Microsoft.AspNetCore.Diagnostics;
    var statusCodePagesFeature = HttpContext.Features.Get<IStatusCodePagesFeature>();

    if (statusCodePagesFeature != null)
    {
        statusCodePagesFeature.Enabled = false;
    }
}
```

## Exception-handling code

Code in exception handling pages can also throw exceptions. Production error pages should be tested thoroughly and take extra care to avoid throwing exceptions of their own.

### Response headers

Once the headers for a response are sent:

- The app can't change the response's status code.
- Any exception pages or handlers can't run. The response must be completed or the connection aborted.

## Server exception handling

In addition to the exception handling logic in an app, the [HTTP server implementation](servers/?view=aspnetcore-10.0) can handle some exceptions. If the server catches an exception before response headers are sent, the server sends a `500 - Internal Server Error` response without a response body. If the server catches an exception after response headers are sent, the server closes the connection. Requests that aren't handled by the app are handled by the server. Any exception that occurs when the server is handling the request is handled by the server's exception handling. The app's custom error pages, exception handling middleware, and filters don't affect this behavior.

## Startup exception handling

Only the hosting layer can handle exceptions that take place during app startup. The host can be configured to [capture startup errors](host/web-host?view=aspnetcore-10.0#capture-startup-errors) and [capture detailed errors](host/web-host?view=aspnetcore-10.0#detailed-errors).

The hosting layer can show an error page for a captured startup error only if the error occurs after host address/port binding. If binding fails:

- The hosting layer logs a critical exception.
- The dotnet process crashes.
- No error page is displayed when the HTTP server is [Kestrel](servers/kestrel?view=aspnetcore-10.0).

When running on [IIS](/en-us/iis) (or Azure App Service) or [IIS Express](/en-us/iis/extensions/introduction-to-iis-express/iis-express-overview), a *502.5 - Process Failure* is returned by the [ASP.NET Core Module](../host-and-deploy/aspnet-core-module?view=aspnetcore-10.0) if the process can't start. For more information, see [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0).

## Database error page

The Database developer page exception filter `AddDatabaseDeveloperPageExceptionFilter` captures database-related exceptions that can be resolved by using Entity Framework Core migrations. When these exceptions occur, an HTML response is generated with details of possible actions to resolve the issue. This page is enabled only in the `Development` environment. The following code was generated by the ASP.NET Core Razor Pages templates when individual user accounts were specified:

```
public void ConfigureServices(IServiceCollection services)
{
    services.AddDbContext<ApplicationDbContext>(options =>
        options.UseSqlServer(
            Configuration.GetConnectionString("DefaultConnection")));
    services.AddDatabaseDeveloperPageExceptionFilter();
    services.AddDefaultIdentity<IdentityUser>(options => options.SignIn.RequireConfirmedAccount = true)
        .AddEntityFrameworkStores<ApplicationDbContext>();
    services.AddRazorPages();
}
```

## Exception filters

In MVC apps, exception filters can be configured globally or on a per-controller or per-action basis. In Razor Pages apps, they can be configured globally or per page model. These filters handle any unhandled exceptions that occur during the execution of a controller action or another filter. For more information, see [Filters in ASP.NET Core](../mvc/controllers/filters?view=aspnetcore-10.0#exception-filters).

Exception filters are useful for trapping exceptions that occur within MVC actions, but they're not as flexible as the built-in [exception handling middleware](https://github.com/dotnet/aspnetcore/blob/main/src/Middleware/Diagnostics/src/ExceptionHandler/ExceptionHandlerMiddleware.cs), `UseExceptionHandler`. We recommend using `UseExceptionHandler`, unless you need to perform error handling differently based on which MVC action is chosen.

```
public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
{
    if (env.IsDevelopment())
    {
        app.UseDeveloperExceptionPage();
    }
    else
    {
        app.UseExceptionHandler("/Error");
        app.UseHsts();
    }

    app.UseHttpsRedirection();
    app.UseStaticFiles();

    app.UseRouting();

    app.UseAuthorization();

    app.UseEndpoints(endpoints =>
    {
        endpoints.MapRazorPages();
    });
}
```

## Model state errors

For information about how to handle model state errors, see [Model binding](../mvc/models/model-binding?view=aspnetcore-10.0) and [Model validation](../mvc/models/validation?view=aspnetcore-10.0).

## Additional resources

- [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0)
- [Common error troubleshooting for Azure App Service and IIS with ASP.NET Core](../host-and-deploy/azure-iis-errors-reference?view=aspnetcore-10.0)

By [Tom Dykstra](https://github.com/tdykstra/), and [Steve Smith](https://ardalis.com/)

This article covers common approaches to handling errors in ASP.NET Core web apps. See [Handle errors in ASP.NET Core APIs](error-handling-api?view=aspnetcore-10.0) for web APIs.

[View or download sample code](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples). ([How to download](./?view=aspnetcore-10.0#how-to-download-a-sample).)

## Developer Exception Page

The *Developer Exception Page* displays detailed information about request exceptions. The ASP.NET Core templates generate the following code:

```
if (env.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}
else
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}
```

The preceding code enables the developer exception page when the app is running in the [`Development` environment](environments?view=aspnetcore-10.0).

The templates place [UseDeveloperExceptionPage](/en-us/dotnet/api/microsoft.aspnetcore.builder.developerexceptionpageextensions.usedeveloperexceptionpage) before any middleware so exceptions are caught in the middleware that follows.

The preceding code enables the Developer Exception Page **only when the app is running in the `Development` environment**. Detailed exception information should not be displayed publicly when the app runs in production. For more information on configuring environments, see [ASP.NET Core runtime environments](environments?view=aspnetcore-10.0).

The Developer Exception Page includes the following information about the exception and the request:

- Stack trace
- Query string parameters if any
- Cookies if any
- Headers

## Exception handler page

To configure a custom error handling page for the `Production` environment, use the exception handling middleware. The middleware:

- Catches and logs exceptions.
- Re-executes the request in an alternate pipeline for the page or controller indicated. The request isn't re-executed if the response has started. The template generated code re-executes the request to `/Error`.

In the following example, [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler) adds the exception handling middleware in non-`Development` environments:

```
if (env.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}
else
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}
```

The Razor Pages app template provides an Error page (`.cshtml`) and [PageModel](/en-us/dotnet/api/microsoft.aspnetcore.mvc.razorpages.pagemodel) class (`ErrorModel`) in the *Pages* folder. For an MVC app, the project template includes an Error action method and an Error view in the Home controller.

Don't mark the error handler action method with HTTP method attributes, such as `HttpGet`. Explicit verbs prevent some requests from reaching the method. Allow anonymous access to the method if unauthenticated users should see the error view.

### Access the exception

Use [IExceptionHandlerPathFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandlerpathfeature) to access the exception and the original request path in an error handler controller or page:

```
[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
public class ErrorModel : PageModel
{
    public string RequestId { get; set; }
    public bool ShowRequestId => !string.IsNullOrEmpty(RequestId);
    public string ExceptionMessage { get; set; }

    public void OnGet()
    {
        RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;

        var exceptionHandlerPathFeature =
            HttpContext.Features.Get<IExceptionHandlerPathFeature>();
        if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
        {
            ExceptionMessage = "File error thrown";
        }
        if (exceptionHandlerPathFeature?.Path == "/index")
        {
            ExceptionMessage += " from home page";
        }
    }
}
```

Warning

Do **not** serve sensitive error information to clients. Serving errors is a security risk.

To trigger the preceding exception handling page, set the environment to productions and force an exception.

## Exception handler lambda

An alternative to a [custom exception handler page](#exception-handler-page) is to provide a lambda to [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). Using a lambda allows access to the error before returning the response.

Here's an example of using a lambda for exception handling:

```
if (env.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}
else
{
   app.UseExceptionHandler(errorApp =>
   {
        errorApp.Run(async context =>
        {
            context.Response.StatusCode = (int) HttpStatusCode.InternalServerError;
            context.Response.ContentType = "text/html";

            await context.Response.WriteAsync("<html lang=\"en\"><body>\r\n");
            await context.Response.WriteAsync("ERROR!<br><br>\r\n");

            var exceptionHandlerPathFeature = 
                context.Features.Get<IExceptionHandlerPathFeature>();

            if (exceptionHandlerPathFeature?.Error is FileNotFoundException)
            {
                await context.Response.WriteAsync("File error thrown!<br><br>\r\n");
            }

            await context.Response.WriteAsync("<a href=\"/\">Home</a><br>\r\n");
            await context.Response.WriteAsync("</body></html>\r\n");
            await context.Response.WriteAsync(new string(' ', 512)); // IE padding
        });
    });
    app.UseHsts();
}
```

In the preceding code, `await context.Response.WriteAsync(new string(' ', 512));` is added so the Internet Explorer browser displays the error message rather than an IE error message. For more information, see [this GitHub issue](https://github.com/dotnet/AspNetCore.Docs/issues/16144).

Warning

Do **not** serve sensitive error information from [IExceptionHandlerFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandlerfeature) or [IExceptionHandlerPathFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandlerpathfeature) to clients. Serving errors is a security risk.

To see the result of the exception handling lambda in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples), use the `ProdEnvironment` and `ErrorHandlerLambda` preprocessor directives, and select **Trigger an exception** on the home page.

## UseStatusCodePages

By default, an ASP.NET Core app doesn't provide a status code page for HTTP status codes, such as *404 - Not Found*. The app returns a status code and an empty response body. To provide status code pages, use Status Code Pages middleware.

The middleware is made available by the [Microsoft.AspNetCore.Diagnostics](https://www.nuget.org/packages/Microsoft.AspNetCore.Diagnostics/) package.

To enable default text-only handlers for common error status codes, call [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) in the `Startup.Configure` method:

```
app.UseStatusCodePages();
```

Call `UseStatusCodePages` before request handling middleware (for example, static file middleware and MVC middleware).

When `UseStatusCodePages` isn't used, navigating to a URL without an endpoint returns a browser dependent error message indicating the endpoint can't be found. For example, navigating to `Home/Privacy2`. When `UseStatusCodePages` is called, the browser returns:

```
Status Code: 404; Not Found
```

## UseStatusCodePages with format string

To customize the response content type and text, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a content type and format string:

```
app.UseStatusCodePages(
    "text/plain", "Status code page, status code: {0}");
```

## UseStatusCodePages with lambda

To specify custom error-handling and response-writing code, use the overload of [UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) that takes a lambda expression:

```
app.UseStatusCodePages(async context =>
{
    context.HttpContext.Response.ContentType = "text/plain";

    await context.HttpContext.Response.WriteAsync(
        "Status code page, status code: " + 
        context.HttpContext.Response.StatusCode);
});
```

## UseStatusCodePagesWithRedirects

The [UseStatusCodePagesWithRedirects](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithredirects) extension method:

- Sends a *302 - Found* status code to the client.
- Redirects the client to the location provided in the URL template.

```
app.UseStatusCodePagesWithRedirects("/StatusCode?code={0}");
```

The URL template can include a `{0}` placeholder for the status code, as shown in the example. If the URL template starts with `~` (tilde), the `~` is replaced by the app's `PathBase`. If you point to an endpoint within the app, create an MVC view or Razor page for the endpoint. For a Razor Pages example, see `Pages/StatusCode.cshtml` in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples).

This method is commonly used when the app:

- Should redirect the client to a different endpoint, usually in cases where a different app processes the error. For web apps, the client's browser address bar reflects the redirected endpoint.
- Shouldn't preserve and return the original status code with the initial redirect response.

## UseStatusCodePagesWithReExecute

The [UseStatusCodePagesWithReExecute](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepageswithreexecute) extension method:

- Returns the original status code to the client.
- Generates the response body by re-executing the request pipeline using an alternate path.

```
app.UseStatusCodePagesWithReExecute("/StatusCode","?code={0}");
```

If you point to an endpoint within the app, create an MVC view or Razor page for the endpoint. Ensure `UseStatusCodePagesWithReExecute` is placed before `UseRouting` so the request can be rerouted to the status page. For a Razor Pages example, see `Pages/StatusCode.cshtml` in the [sample app](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/error-handling/samples).

This method is commonly used when the app should:

- Process the request without redirecting to a different endpoint. For web apps, the client's browser address bar reflects the originally requested endpoint.
- Preserve and return the original status code with the response.

The URL and query string templates may include a placeholder (`{0}`) for the status code. The URL template must start with a slash (`/`). When using a placeholder in the path, confirm that the endpoint (page or controller) can process the path segment. For example, a Razor Page for errors should accept the optional path segment value with the `@page` directive:

```
@page "{code?}"
```

The endpoint that processes the error can get the original URL that generated the error, as shown in the following example:

```
var statusCodeReExecuteFeature = HttpContext.Features.Get<IStatusCodeReExecuteFeature>();
if (statusCodeReExecuteFeature != null)
{
    OriginalURL =
        statusCodeReExecuteFeature.OriginalPathBase
        + statusCodeReExecuteFeature.OriginalPath
        + statusCodeReExecuteFeature.OriginalQueryString;
}
```

Don't mark the error handler action method with HTTP method attributes, such as `HttpGet`. Explicit verbs prevent some requests from reaching the method. Allow anonymous access to the method if unauthenticated users should see the error view.

## Disable status code pages

To disable status code pages for an MVC controller or action method, use the [`[SkipStatusCodePages]`](/en-us/dotnet/api/microsoft.aspnetcore.mvc.skipstatuscodepagesattribute) attribute.

To disable status code pages for specific requests in a Razor Pages handler method or in an MVC controller, use [IStatusCodePagesFeature](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.istatuscodepagesfeature):

```
var statusCodePagesFeature = HttpContext.Features.Get<IStatusCodePagesFeature>();

if (statusCodePagesFeature != null)
{
    statusCodePagesFeature.Enabled = false;
}
```

## Exception-handling code

Code in exception handling pages can throw exceptions. It's often a good idea for production error pages to consist of purely static content.

### Response headers

Once the headers for a response are sent:

- The app can't change the response's status code.
- Any exception pages or handlers can't run. The response must be completed or the connection aborted.

## Server exception handling

In addition to the exception handling logic in your app, the [HTTP server implementation](servers/?view=aspnetcore-10.0) can handle some exceptions. If the server catches an exception before response headers are sent, the server sends a *500 - Internal Server Error* response without a response body. If the server catches an exception after response headers are sent, the server closes the connection. Requests that aren't handled by your app are handled by the server. Any exception that occurs when the server is handling the request is handled by the server's exception handling. The app's custom error pages, exception handling middleware, and filters don't affect this behavior.

## Startup exception handling

Only the hosting layer can handle exceptions that take place during app startup. The host can be configured to [capture startup errors](host/web-host?view=aspnetcore-10.0#capture-startup-errors) and [capture detailed errors](host/web-host?view=aspnetcore-10.0#detailed-errors).

The hosting layer can show an error page for a captured startup error only if the error occurs after host address/port binding. If binding fails:

- The hosting layer logs a critical exception.
- The dotnet process crashes.
- No error page is displayed when the HTTP server is [Kestrel](servers/kestrel?view=aspnetcore-10.0).

When running on [IIS](/en-us/iis) (or Azure App Service) or [IIS Express](/en-us/iis/extensions/introduction-to-iis-express/iis-express-overview), a *502.5 - Process Failure* is returned by the [ASP.NET Core Module](../host-and-deploy/aspnet-core-module?view=aspnetcore-10.0) if the process can't start. For more information, see [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0).

## Database error page

Database error page middleware captures database-related exceptions that can be resolved by using Entity Framework migrations. When these exceptions occur, an HTML response with details of possible actions to resolve the issue is generated. This page should be enabled only in the `Development` environment. Enable the page by adding code to `Startup.Configure`:

```
if (env.IsDevelopment())
{
    app.UseDatabaseErrorPage();
}
```

[UseDatabaseErrorPage](/en-us/dotnet/api/microsoft.aspnetcore.builder.databaseerrorpageextensions.usedatabaseerrorpage) requires the [Microsoft.AspNetCore.Diagnostics.EntityFrameworkCore](https://www.nuget.org/packages/Microsoft.AspNetCore.Diagnostics.EntityFrameworkCore/) NuGet package.

## Exception filters

In MVC apps, exception filters can be configured globally or on a per-controller or per-action basis. In Razor Pages apps, they can be configured globally or per page model. These filters handle any unhandled exception that occurs during the execution of a controller action or another filter. For more information, see [Filters in ASP.NET Core](../mvc/controllers/filters?view=aspnetcore-10.0#exception-filters).

Tip

Exception filters are useful for trapping exceptions that occur within MVC actions, but they're not as flexible as the exception handling middleware. We recommend using the middleware. Use filters only where you need to perform error handling differently based on which MVC action is chosen.

## Model state errors

For information about how to handle model state errors, see [Model binding](../mvc/models/model-binding?view=aspnetcore-10.0) and [Model validation](../mvc/models/validation?view=aspnetcore-10.0).

## Additional resources

- [Troubleshoot ASP.NET Core on Azure App Service and IIS](../test/troubleshoot-azure-iis?view=aspnetcore-10.0)
- [Common error troubleshooting for Azure App Service and IIS with ASP.NET Core](../host-and-deploy/azure-iis-errors-reference?view=aspnetcore-10.0)

---

## Additional resources

---

- Last updated on 
  2026-08-10
