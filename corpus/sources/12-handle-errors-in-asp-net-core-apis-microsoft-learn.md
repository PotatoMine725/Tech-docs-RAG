# Handle errors in ASP.NET Core APIs - Microsoft Learn

Source: https://learn.microsoft.com/en-us/aspnet/core/fundamentals/error-handling-api?view=aspnetcore-10.0

---

---

Note

Access to this page requires authorization. You can try [signing in](#) or changing directories.

Access to this page requires authorization. You can try changing directories.

# Handle errors in ASP.NET Core APIs

Note

This isn't the latest version of this article. For the current release, see the [.NET 10 version of this article](?view=aspnetcore-10.0&preserve-view=true).

Warning

This version of ASP.NET Core is no longer supported. For more information, see the [.NET and .NET Core Support Policy](https://dotnet.microsoft.com/platform/support/policy/dotnet-core). For the current release, see the [.NET 10 version of this article](?view=aspnetcore-10.0&preserve-view=true).

- [Minimal APIs](#tabpanel_1_minimal-apis)
- [Controllers](#tabpanel_1_controllers)

This article describes how to handle errors in ASP.NET Core APIs. Documentation for Minimal APIs is selected. To see documentation for controller-based APIs, select the **Controllers** tab. For Blazor error handling guidance, see [Handle errors in ASP.NET Core Blazor apps](../blazor/fundamentals/handle-errors?view=aspnetcore-10.0).

This article describes how to handle errors in ASP.NET Core APIs. Documentation for Controller-based APIs is selected. To see documentation for **Minimal APIs**, select the **Minimal APIs** tab. For Blazor error handling guidance, see [Handle errors in ASP.NET Core Blazor apps](../blazor/fundamentals/handle-errors?view=aspnetcore-10.0).

## Developer Exception Page

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

- [Minimal APIs](#tabpanel_2_minimal-apis)
- [Controllers](#tabpanel_2_controllers)

To see the Developer Exception Page in a Minimal API:

- Run the sample app in the [`Development` environment](environments?view=aspnetcore-10.0).
- Go to the `/exception` endpoint.

This section refers to the following sample app to demonstrate ways to handle exceptions in a Minimal API. It throws an exception when the endpoint `/exception` is requested:

```
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/exception", () => 
{
    throw new InvalidOperationException("Sample Exception");
});

app.MapGet("/", () => "Test by calling /exception");

app.Run();
```

To see the Developer Exception Page in a controller-based API:

- Add the following controller action to a controller-based API. The action throws an exception when the endpoint is requested.

  ```
  [HttpGet("Throw")]
  public IActionResult Throw() =>
      throw new Exception("Sample exception.");
  ```
- Run the app in the [development environment](environments?view=aspnetcore-10.0).
- Go to the endpoint defined by the controller action.

## Exception handler

In non-development environments, use the [exception handler middleware](error-handling?view=aspnetcore-10.0#exception-handler-page) to produce an error payload.

- [Minimal APIs](#tabpanel_3_minimal-apis)
- [Controllers](#tabpanel_3_controllers)

To configure the `exception handler middleware`, call [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler). For example, the following code changes the app to respond with an [RFC 7807](https://tools.ietf.org/html/rfc7807)-compliant payload to the client. For more information, see the [Problem Details](#problem-details) section later in this article.

```
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.UseExceptionHandler(exceptionHandlerApp 
    => exceptionHandlerApp.Run(async context 
        => await Results.Problem()
                     .ExecuteAsync(context)));

app.MapGet("/exception", () => 
{
    throw new InvalidOperationException("Sample Exception");
});

app.MapGet("/", () => "Test by calling /exception");

app.Run();
```

1. In `Program.cs`, call [UseExceptionHandler](/en-us/dotnet/api/microsoft.aspnetcore.builder.exceptionhandlerextensions.useexceptionhandler) to add the exception handling middleware:

   ```
   var app = builder.Build();

   app.UseHttpsRedirection();

   if (!app.Environment.IsDevelopment())
   {
       app.UseExceptionHandler("/error");
   }

   app.UseAuthorization();

   app.MapControllers();

   app.Run();
   ```
2. Configure a controller action to respond to the `/error` route:

   ```
   [Route("/error")]
   public IActionResult HandleError() =>
       Problem();
   ```

The preceding `HandleError` action sends an [RFC 7807](https://tools.ietf.org/html/rfc7807)-compliant payload to the client.

Warning

Don't mark the error handler action method with HTTP method attributes, such as `HttpGet`. Explicit verbs prevent some requests from reaching the action method.

For web APIs that use [Swagger / OpenAPI](../tutorials/web-api-help-pages-using-swagger?view=aspnetcore-10.0), mark the error handler action with the [[ApiExplorerSettings]](/en-us/dotnet/api/microsoft.aspnetcore.mvc.apiexplorersettingsattribute) attribute and set its [IgnoreApi](/en-us/dotnet/api/microsoft.aspnetcore.mvc.apiexplorersettingsattribute.ignoreapi) property to `true`. This attribute configuration excludes the error handler action from the app's OpenAPI specification:

```
[ApiExplorerSettings(IgnoreApi = true)]
```

Allow anonymous access to the method if unauthenticated users should see the error.

## Client and Server error responses

- [Minimal APIs](#tabpanel_4_minimal-apis)
- [Controllers](#tabpanel_4_controllers)

Consider the following Minimal API app.

```
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/users/{id:int}", (int id) 
    => id <= 0 ? Results.BadRequest() : Results.Ok(new User(id)));

app.MapGet("/", () => "Test by calling /users/{id:int}");

app.Run();

public record User(int Id);
```

The `/users` endpoint produces `200 OK` with a `json` representation of `User` when `id` is greater than `0`, otherwise a `400 BAD REQUEST` status code without a response body. For more information about creating a response, see [Create responses in Minimal API apps](/en-us/aspnet/core/fundamentals/minimal-apis/responses).

The [`Status Code Pages middleware`](#client-and-server-error-responses) can be configured to produce a common body content, **when empty**, for all HTTP client (`400`-`499`) or server (`500` -`599`) responses. The middleware is configured by calling the
[UseStatusCodePages](/en-us/dotnet/api/microsoft.aspnetcore.builder.statuscodepagesextensions.usestatuscodepages) extension method.

For example, the following example changes the app to respond with an [RFC 7807](https://tools.ietf.org/html/rfc7807)-compliant payload to the client for all client and server responses, including routing errors (for example, `404 NOT FOUND`). For more information, see the [Problem Details](#problem-details) section.

```
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.UseStatusCodePages(async statusCodeContext 
    => await Results.Problem(statusCode: statusCodeContext.HttpContext.Response.StatusCode)
                 .ExecuteAsync(statusCodeContext.HttpContext));

app.MapGet("/users/{id:int}", (int id) 
    => id <= 0 ? Results.BadRequest() : Results.Ok(new User(id)) );

app.MapGet("/", () => "Test by calling /users/{id:int}");

app.Run();

public record User(int Id);
```

For controller-based APIs, the error response can be configured in one of the following ways:

1. Use the [problem details service](#problem-details-service)
2. [Implement ProblemDetailsFactory](#implement-problemdetailsfactory)
3. [Use ApiBehaviorOptions.ClientErrorMapping](#use-apibehavioroptionsclienterrormapping)

An *error result* is defined as a result with an HTTP status code of 400 or higher. For web API controllers, MVC transforms an error result to produce a [ProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.mvc.problemdetails).

The automatic creation of a `ProblemDetails` for error status codes is enabled by default.

## Problem details

[Problem Details](https://www.rfc-editor.org/rfc/rfc7807.html) are not the only response format to describe an HTTP API error, however, they are commonly used to report errors for HTTP APIs.

The problem details service implements the [IProblemDetailsService](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice) interface, which supports creating problem details in ASP.NET Core. The [AddProblemDetails(IServiceCollection)](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.problemdetailsservicecollectionextensions.addproblemdetails#microsoft-extensions-dependencyinjection-problemdetailsservicecollectionextensions-addproblemdetails(microsoft-extensions-dependencyinjection-iservicecollection)) extension method on [IServiceCollection](/en-us/dotnet/api/microsoft.extensions.dependencyinjection.iservicecollection) registers the default `IProblemDetailsService` implementation.

In ASP.NET Core apps, the following middleware generates problem details HTTP responses when `AddProblemDetails` is called, except when the [`Accept` request HTTP header](https://developer.mozilla.org/docs/Web/HTTP/Headers/Accept) doesn't include one of the content types supported by the registered [IProblemDetailsWriter](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailswriter) (default: `application/json`):

- [ExceptionHandlerMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.exceptionhandlermiddleware): Generates a problem details response when a custom handler is not defined.
- [StatusCodePagesMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.statuscodepagesmiddleware): Generates a problem details response by default.
- [DeveloperExceptionPageMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.diagnostics.developerexceptionpagemiddleware): Generates a problem details response in development when the `Accept` request HTTP header doesn't include `text/html`.

- [Minimal APIs](#tabpanel_5_minimal-apis)
- [Controllers](#tabpanel_5_controllers)

Minimal API apps can be configured to generate problem details response for all HTTP client and server error responses that ***don't have body content yet*** by using the `AddProblemDetails` extension method.

The following code configures the app to generate problem details:

```
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();

app.MapGet("/users/{id:int}", (int id) 
    => id <= 0 ? Results.BadRequest() : Results.Ok(new User(id)));

app.MapGet("/", () => "Test by calling /users/{id:int}");

app.Run();

public record User(int Id);
```

For more information on using `AddProblemDetails`, see [Problem Details](#problem-details)

### IProblemDetailsService fallback

In the following code, `httpContext.Response.WriteAsync("Fallback: An error occurred.")` returns an error if the [IProblemDetailsService](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice) implementation isn't able to generate a [ProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.mvc.problemdetails):

```
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler(exceptionHandlerApp =>
{
    exceptionHandlerApp.Run(async httpContext =>
    {
        var pds = httpContext.RequestServices.GetService<IProblemDetailsService>();
        if (pds == null
            || !await pds.TryWriteAsync(new() { HttpContext = httpContext }))
        {
            // Fallback behavior
            await httpContext.Response.WriteAsync("Fallback: An error occurred.");
        }
    });
});

app.MapGet("/exception", () =>
{
    throw new InvalidOperationException("Sample Exception");
});

app.MapGet("/", () => "Test by calling /exception");

app.Run();
```

The preceding code:

- Writes an error message with the fallback code if the `problemDetailsService` is unable to write a `ProblemDetails`. For example, an endpoint where the [Accept request header](https://developer.mozilla.org/docs/Web/HTTP/Headers/Accept) specifies a media type that the `DefaultProblemDetailsWriter` does not support.
- Uses the [exception handler middleware](#exception-handler).

Note

The `DefaultProblemDetailsWriter` supports the following media types in the `Accept` request header:

- `application/json`
- `application/problem+json`
- Wildcard types such as `*/*` and `application/*`

Non-JSON media types, such as `application/xml` or `text/html`, are **not** supported and trigger the fallback behavior.

The following sample is similar to the preceding except that it calls the [`Status Code Pages middleware`](#client-and-server-error-responses).

```
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseStatusCodePages(statusCodeHandlerApp =>
{
    statusCodeHandlerApp.Run(async httpContext =>
    {
        var pds = httpContext.RequestServices.GetService<IProblemDetailsService>();
        if (pds == null
            || !await pds.TryWriteAsync(new() { HttpContext = httpContext }))
        {
            // Fallback behavior
            await httpContext.Response.WriteAsync("Fallback: An error occurred.");
        }
    });
});

app.MapGet("/users/{id:int}", (int id) =>
{
    return id <= 0 ? Results.BadRequest() : Results.Ok(new User(id));
});

app.MapGet("/", () => "Test by calling /users/{id:int}");

app.Run();

public record User(int Id);
```

### Problem details service

ASP.NET Core supports creating [Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457) using the [IProblemDetailsService](/en-us/dotnet/api/microsoft.aspnetcore.http.iproblemdetailsservice).

The following code configures the app to generate a problem details response for all HTTP client and server error responses that ***don't have body content yet***:

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

Consider the API controller from the preceding section, which returns [BadRequest](/en-us/dotnet/api/microsoft.aspnetcore.http.httpresults.badrequest) when the input is invalid:

```
[Route("api/[controller]/[action]")]
[ApiController]
public class Values2Controller : ControllerBase
{
    // /api/values2/divide/1/2
    [HttpGet("{Numerator}/{Denominator}")]
    public IActionResult Divide(double Numerator, double Denominator)
    {
        if (Denominator == 0)
        {
            return BadRequest();
        }

        return Ok(Numerator / Denominator);
    }

    // /api/values2 /squareroot/4
    [HttpGet("{radicand}")]
    public IActionResult Squareroot(double radicand)
    {
        if (radicand < 0)
        {
            return BadRequest();
        }

        return Ok(Math.Sqrt(radicand));
    }
}
```

A problem details response is generated with the preceding code when any of the following conditions apply:

- An invalid input is supplied.
- The URI has no matching endpoint.
- An unhandled exception occurs.

#### Customize problem details with `CustomizeProblemDetails`

The following code uses [ProblemDetailsOptions](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions) to set [CustomizeProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.http.problemdetailsoptions.customizeproblemdetails#microsoft-aspnetcore-http-problemdetailsoptions-customizeproblemdetails):

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

builder.Services.AddProblemDetails(options =>
        options.CustomizeProblemDetails = (context) =>
        {

            var mathErrorFeature = context.HttpContext.Features
                                                       .Get<MathErrorFeature>();
            if (mathErrorFeature is not null)
            {
                (string Detail, string Type) details = mathErrorFeature.MathError switch
                {
                    MathErrorType.DivisionByZeroError =>
                    ("Divison by zero is not defined.",
                                          "https://wikipedia.org/wiki/Division_by_zero"),
                    _ => ("Negative or complex numbers are not valid input.",
                                          "https://wikipedia.org/wiki/Square_root")
                };

                context.ProblemDetails.Type = details.Type;
                context.ProblemDetails.Title = "Bad Input";
                context.ProblemDetails.Detail = details.Detail;
            }
        }
    );

var app = builder.Build();

app.UseHttpsRedirection();

app.UseStatusCodePages();

app.UseAuthorization();

app.MapControllers();

app.Run();
```

### Implement `ProblemDetailsFactory`

MVC uses [Microsoft.AspNetCore.Mvc.Infrastructure.ProblemDetailsFactory](/en-us/dotnet/api/microsoft.aspnetcore.mvc.infrastructure.problemdetailsfactory) to produce all instances of [ProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.mvc.problemdetails) and [ValidationProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.mvc.validationproblemdetails). This factory is used for:

- Client error responses
- Validation failure error responses
- [ControllerBase.Problem](/en-us/dotnet/api/microsoft.aspnetcore.mvc.controllerbase.problem) and [ControllerBase.ValidationProblem](/en-us/dotnet/api/microsoft.aspnetcore.mvc.controllerbase.validationproblem)

To customize the problem details response, register a custom implementation of [ProblemDetailsFactory](/en-us/dotnet/api/microsoft.aspnetcore.mvc.infrastructure.problemdetailsfactory) in `Program.cs`:

```
builder.Services.AddControllers();
builder.Services.AddTransient<ProblemDetailsFactory, SampleProblemDetailsFactory>();
```

### Use `ApiBehaviorOptions.ClientErrorMapping`

Use the [ClientErrorMapping](/en-us/dotnet/api/microsoft.aspnetcore.mvc.apibehavioroptions.clienterrormapping) property to configure the contents of the `ProblemDetails` response. For example, the following code in `Program.cs` updates the [Link](/en-us/dotnet/api/microsoft.aspnetcore.mvc.clienterrordata.link) property for 404 responses:

```
builder.Services.AddControllers()
    .ConfigureApiBehaviorOptions(options =>
    {
        options.ClientErrorMapping[StatusCodes.Status404NotFound].Link =
            "https://httpstatuses.com/404";
    });
```

## Additional error handling features

- [Minimal APIs](#tabpanel_6_minimal-apis)
- [Controllers](#tabpanel_6_controllers)

### Migration from controllers to Minimal APIs

If you're migrating from controller-based APIs to Minimal APIs:

1. **Replace action filters** with endpoint filters or middleware
2. **Replace model validation** with manual validation or custom binding
3. **Replace exception filters** with exception handling middleware
4. **Configure problem details** using `AddProblemDetails()` for consistent error responses

### When to use controller-based error handling

Consider controller-based APIs if you need:

- Complex model validation scenarios
- Centralized exception handling across multiple controllers
- Fine-grained control over error response formatting
- Integration with MVC features like filters and conventions

For detailed information about controller-based error handling, including validation errors, problem details customization, and exception filters, see the [Controllers](?view=aspnetcore-10.0&tabs=controllers) tab sections.

### Validation failure error response

For web API controllers, MVC responds with a [ValidationProblemDetails](/en-us/dotnet/api/microsoft.aspnetcore.mvc.validationproblemdetails) response type when model validation fails. MVC uses the results of [InvalidModelStateResponseFactory](/en-us/dotnet/api/microsoft.aspnetcore.mvc.apibehavioroptions.invalidmodelstateresponsefactory#microsoft-aspnetcore-mvc-apibehavioroptions-invalidmodelstateresponsefactory) to construct the error response for a validation failure. The following example replaces the default factory with an implementation that also supports formatting responses as XML, in `Program.cs`:

```
builder.Services.AddControllers()
    .ConfigureApiBehaviorOptions(options =>
    {
        options.InvalidModelStateResponseFactory = context =>
            new BadRequestObjectResult(context.ModelState)
            {
                ContentTypes =
                {
                    // using static System.Net.Mime.MediaTypeNames;
                    Application.Json,
                    Application.Xml
                }
            };
    })
    .AddXmlSerializerFormatters();
```

### Use exceptions to modify the response

The contents of the response can be modified from outside of the controller using a custom exception and an action filter:

1. Create a well-known exception type named `HttpResponseException`:

   ```
   public class HttpResponseException : Exception
   {
       public HttpResponseException(int statusCode, object? value = null) =>
           (StatusCode, Value) = (statusCode, value);

       public int StatusCode { get; }

       public object? Value { get; }
   }
   ```
2. Create an action filter named `HttpResponseExceptionFilter`:

   ```
   public class HttpResponseExceptionFilter : IActionFilter, IOrderedFilter
   {
       public int Order => int.MaxValue - 10;

       public void OnActionExecuting(ActionExecutingContext context) { }

       public void OnActionExecuted(ActionExecutedContext context)
       {
           if (context.Exception is HttpResponseException httpResponseException)
           {
               context.Result = new ObjectResult(httpResponseException.Value)
               {
                   StatusCode = httpResponseException.StatusCode
               };

               context.ExceptionHandled = true;
           }
       }
   }
   ```

   The preceding filter specifies an `Order` of the maximum integer value minus 10. This `Order` allows other filters to run at the end of the pipeline.
3. In `Program.cs`, add the action filter to the filters collection:

   ```
   builder.Services.AddControllers(options =>
   {
       options.Filters.Add<HttpResponseExceptionFilter>();
   });
   ```

### Key differences for controllers

- **Automatic model validation**: Controllers automatically validate model state and return `400 Bad Request` responses for validation failures
- **Exception filters**: Use action filters and exception filters for centralized error handling
- **Built-in problem details**: Configure `ApiBehaviorOptions` for standardized error responses
- **Custom error responses**: Override `InvalidModelStateResponseFactory` for custom validation error formatting

## Additional resources

- [How to Use ModelState Validation in ASP.NET Core Web API](https://code-maze.com/aspnetcore-modelstate-validation-web-api/)
- [View or download sample code](https://github.com/dotnet/AspNetCore.Docs.Samples/tree/main/fundamentals/middleware/problem-details-service)
- [Hellang.Middleware.ProblemDetails](https://www.nuget.org/packages/Hellang.Middleware.ProblemDetails/)

---

## Additional resources

---

- Last updated on 
  2026-03-04
