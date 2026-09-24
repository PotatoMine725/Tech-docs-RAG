# Factory-based middleware activation in ASP.NET Core - Microsoft Learn

Source: https://learn.microsoft.com/en-us/aspnet/core/fundamentals/middleware/extensibility?view=aspnetcore-10.0

---

---

Note

Access to this page requires authorization. You can try [signing in](#) or changing directories.

Access to this page requires authorization. You can try changing directories.

# Factory-based middleware activation in ASP.NET Core

Note

This isn't the latest version of this article. For the current release, see the [.NET 10 version of this article](?view=aspnetcore-10.0&preserve-view=true).

Warning

This version of ASP.NET Core is no longer supported. For more information, see the [.NET and .NET Core Support Policy](https://dotnet.microsoft.com/platform/support/policy/dotnet-core). For the current release, see the [.NET 10 version of this article](?view=aspnetcore-10.0&preserve-view=true).

[IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory)/[IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is an extensibility point for [middleware](./?view=aspnetcore-10.0) activation that offers the following benefits:

- Activation per client request (injection of scoped services)
- Strong typing of middleware

[UseMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.builder.usemiddlewareextensions.usemiddleware) extension methods check if a middleware's registered type implements [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware). If it does, the [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) instance registered in the container is used to resolve the [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) implementation instead of using the convention-based middleware activation logic. The middleware is registered as a [scoped or transient service](../dependency-injection?view=aspnetcore-10.0#service-lifetimes) in the app's service container.

[IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is activated per client request (connection), so scoped services can be injected into the middleware's constructor.

## IMiddleware

[IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) defines middleware for the app's request pipeline. The [InvokeAsync(HttpContext, RequestDelegate)](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware.invokeasync) method handles requests and returns a [Task](/en-us/dotnet/api/system.threading.tasks.task) that represents the execution of the middleware.

Middleware activated by convention:

```
public class ConventionalMiddleware
{
    private readonly RequestDelegate _next;

    public ConventionalMiddleware(RequestDelegate next)
        => _next = next;

    public async Task InvokeAsync(HttpContext context, SampleDbContext dbContext)
    {
        var keyValue = context.Request.Query["key"];

        if (!string.IsNullOrWhiteSpace(keyValue))
        {
            dbContext.Requests.Add(new Request("Conventional", keyValue));

            await dbContext.SaveChangesAsync();
        }

        await _next(context);
    }
}
```

Middleware activated by [MiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.middlewarefactory):

```
public class FactoryActivatedMiddleware : IMiddleware
{
    private readonly SampleDbContext _dbContext;

    public FactoryActivatedMiddleware(SampleDbContext dbContext)
        => _dbContext = dbContext;

    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        var keyValue = context.Request.Query["key"];

        if (!string.IsNullOrWhiteSpace(keyValue))
        {
            _dbContext.Requests.Add(new Request("Factory", keyValue));

            await _dbContext.SaveChangesAsync();
        }

        await next(context);
    }
}
```

Extensions are created for the middleware:

```
public static class MiddlewareExtensions
{
    public static IApplicationBuilder UseConventionalMiddleware(
        this IApplicationBuilder app)
        => app.UseMiddleware<ConventionalMiddleware>();

    public static IApplicationBuilder UseFactoryActivatedMiddleware(
        this IApplicationBuilder app)
        => app.UseMiddleware<FactoryActivatedMiddleware>();
}
```

It isn't possible to pass objects to the factory-activated middleware with [UseMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.builder.usemiddlewareextensions.usemiddleware):

```
public static IApplicationBuilder UseFactoryActivatedMiddleware(
    this IApplicationBuilder app, bool option)
{
    // Passing 'option' as an argument throws a NotSupportedException at runtime.
    return app.UseMiddleware<FactoryActivatedMiddleware>(option);
}
```

The factory-activated middleware is added to the built-in container in `Program.cs`:

```
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDbContext<SampleDbContext>
    (options => options.UseInMemoryDatabase("SampleDb"));

builder.Services.AddTransient<FactoryActivatedMiddleware>();
```

Both middleware are registered in the request processing pipeline, also in `Program.cs`:

```
var app = builder.Build();

app.UseConventionalMiddleware();
app.UseFactoryActivatedMiddleware();
```

## IMiddlewareFactory

[IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) provides methods to create middleware. The middleware factory implementation is registered in the container as a scoped service.

The default [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) implementation, [MiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.middlewarefactory), is found in the [Microsoft.AspNetCore.Http](https://www.nuget.org/packages/Microsoft.AspNetCore.Http/) package.

## Additional resources

- [View or download sample code](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/middleware/extensibility/samples) ([how to download](../?view=aspnetcore-10.0#how-to-download-a-sample))
- [ASP.NET Core middleware](./?view=aspnetcore-10.0)
- [Middleware activation with a third-party container in ASP.NET Core](extensibility-third-party-container?view=aspnetcore-10.0)

[IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory)/[IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is an extensibility point for [middleware](./?view=aspnetcore-10.0) activation.

[UseMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.builder.usemiddlewareextensions.usemiddleware) extension methods check if a middleware's registered type implements [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware). If it does, the [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) instance registered in the container is used to resolve the [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) implementation instead of using the convention-based middleware activation logic. The middleware is registered as a [scoped or transient service](../dependency-injection?view=aspnetcore-10.0#service-lifetimes) in the app's service container.

Benefits:

- Activation per client request (injection of scoped services)
- Strong typing of middleware

[IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is activated per client request (connection), so scoped services can be injected into the middleware's constructor.

[View or download sample code](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/middleware/extensibility/samples) ([how to download](../?view=aspnetcore-10.0#how-to-download-a-sample))

## IMiddleware

[IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) defines middleware for the app's request pipeline. The [InvokeAsync(HttpContext, RequestDelegate)](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware.invokeasync) method handles requests and returns a [Task](/en-us/dotnet/api/system.threading.tasks.task) that represents the execution of the middleware.

Middleware activated by convention:

```
public class ConventionalMiddleware
{
    private readonly RequestDelegate _next;

    public ConventionalMiddleware(RequestDelegate next)
    {
        _next = next;
    }

    public async Task InvokeAsync(HttpContext context, AppDbContext db)
    {
        var keyValue = context.Request.Query["key"];

        if (!string.IsNullOrWhiteSpace(keyValue))
        {
            db.Add(new Request()
                {
                    DT = DateTime.UtcNow, 
                    MiddlewareActivation = "ConventionalMiddleware", 
                    Value = keyValue
                });

            await db.SaveChangesAsync();
        }

        await _next(context);
    }
}
```

Middleware activated by [MiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.middlewarefactory):

```
public class FactoryActivatedMiddleware : IMiddleware
{
    private readonly AppDbContext _db;

    public FactoryActivatedMiddleware(AppDbContext db)
    {
        _db = db;
    }

    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        var keyValue = context.Request.Query["key"];

        if (!string.IsNullOrWhiteSpace(keyValue))
        {
            _db.Add(new Request()
                {
                    DT = DateTime.UtcNow, 
                    MiddlewareActivation = "FactoryActivatedMiddleware", 
                    Value = keyValue
                });

            await _db.SaveChangesAsync();
        }

        await next(context);
    }
}
```

Extensions are created for the middleware:

```
public static class MiddlewareExtensions
{
    public static IApplicationBuilder UseConventionalMiddleware(
        this IApplicationBuilder builder)
    {
        return builder.UseMiddleware<ConventionalMiddleware>();
    }

    public static IApplicationBuilder UseFactoryActivatedMiddleware(
        this IApplicationBuilder builder)
    {
        return builder.UseMiddleware<FactoryActivatedMiddleware>();
    }
}
```

It isn't possible to pass objects to the factory-activated middleware with [UseMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.builder.usemiddlewareextensions.usemiddleware):

```
public static IApplicationBuilder UseFactoryActivatedMiddleware(
    this IApplicationBuilder builder, bool option)
{
    // Passing 'option' as an argument throws a NotSupportedException at runtime.
    return builder.UseMiddleware<FactoryActivatedMiddleware>(option);
}
```

The factory-activated middleware is added to the built-in container in `Startup.ConfigureServices`:

```
public void ConfigureServices(IServiceCollection services)
{
    services.AddDbContext<AppDbContext>(options =>
        options.UseInMemoryDatabase("InMemoryDb"));

    services.AddTransient<FactoryActivatedMiddleware>();

    services.AddRazorPages();
}
```

Both middleware are registered in the request processing pipeline in `Startup.Configure`:

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
    }

    app.UseConventionalMiddleware();
    app.UseFactoryActivatedMiddleware();

    app.UseStaticFiles();
    app.UseRouting();

    app.UseEndpoints(endpoints =>
    {
        endpoints.MapRazorPages();
    });
}
```

## IMiddlewareFactory

[IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) provides methods to create middleware. The middleware factory implementation is registered in the container as a scoped service.

The default [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) implementation, [MiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.middlewarefactory), is found in the [Microsoft.AspNetCore.Http](https://www.nuget.org/packages/Microsoft.AspNetCore.Http/) package.

## Additional resources

- [ASP.NET Core middleware](./?view=aspnetcore-10.0)
- [Middleware activation with a third-party container in ASP.NET Core](extensibility-third-party-container?view=aspnetcore-10.0)

[IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory)/[IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is an extensibility point for [middleware](./?view=aspnetcore-10.0) activation.

[UseMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.builder.usemiddlewareextensions.usemiddleware) extension methods check if a middleware's registered type implements [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware). If it does, the [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) instance registered in the container is used to resolve the [IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) implementation instead of using the convention-based middleware activation logic. The middleware is registered as a [scoped or transient service](../dependency-injection?view=aspnetcore-10.0#service-lifetimes) in the app's service container.

Benefits:

- Activation per client request (injection of scoped services)
- Strong typing of middleware

[IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) is activated per client request (connection), so scoped services can be injected into the middleware's constructor.

[View or download sample code](https://github.com/dotnet/AspNetCore.Docs/tree/main/aspnetcore/fundamentals/middleware/extensibility/samples) ([how to download](../?view=aspnetcore-10.0#how-to-download-a-sample))

## IMiddleware

[IMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware) defines middleware for the app's request pipeline. The [InvokeAsync(HttpContext, RequestDelegate)](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddleware.invokeasync) method handles requests and returns a [Task](/en-us/dotnet/api/system.threading.tasks.task) that represents the execution of the middleware.

Middleware activated by convention:

```
public class ConventionalMiddleware
{
    private readonly RequestDelegate _next;

    public ConventionalMiddleware(RequestDelegate next)
    {
        _next = next;
    }

    public async Task InvokeAsync(HttpContext context, AppDbContext db)
    {
        var keyValue = context.Request.Query["key"];

        if (!string.IsNullOrWhiteSpace(keyValue))
        {
            db.Add(new Request()
                {
                    DT = DateTime.UtcNow, 
                    MiddlewareActivation = "ConventionalMiddleware", 
                    Value = keyValue
                });

            await db.SaveChangesAsync();
        }

        await _next(context);
    }
}
```

Middleware activated by [MiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.middlewarefactory):

```
public class FactoryActivatedMiddleware : IMiddleware
{
    private readonly AppDbContext _db;

    public FactoryActivatedMiddleware(AppDbContext db)
    {
        _db = db;
    }

    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        var keyValue = context.Request.Query["key"];

        if (!string.IsNullOrWhiteSpace(keyValue))
        {
            _db.Add(new Request()
                {
                    DT = DateTime.UtcNow, 
                    MiddlewareActivation = "FactoryActivatedMiddleware", 
                    Value = keyValue
                });

            await _db.SaveChangesAsync();
        }

        await next(context);
    }
}
```

Extensions are created for the middleware:

```
public static class MiddlewareExtensions
{
    public static IApplicationBuilder UseConventionalMiddleware(
        this IApplicationBuilder builder)
    {
        return builder.UseMiddleware<ConventionalMiddleware>();
    }

    public static IApplicationBuilder UseFactoryActivatedMiddleware(
        this IApplicationBuilder builder)
    {
        return builder.UseMiddleware<FactoryActivatedMiddleware>();
    }
}
```

It isn't possible to pass objects to the factory-activated middleware with [UseMiddleware](/en-us/dotnet/api/microsoft.aspnetcore.builder.usemiddlewareextensions.usemiddleware):

```
public static IApplicationBuilder UseFactoryActivatedMiddleware(
    this IApplicationBuilder builder, bool option)
{
    // Passing 'option' as an argument throws a NotSupportedException at runtime.
    return builder.UseMiddleware<FactoryActivatedMiddleware>(option);
}
```

The factory-activated middleware is added to the built-in container in `Startup.ConfigureServices`:

```
public void ConfigureServices(IServiceCollection services)
{
    services.AddDbContext<AppDbContext>(options =>
        options.UseInMemoryDatabase("InMemoryDb"));

    services.AddTransient<FactoryActivatedMiddleware>();

    services.AddMvc()
        .SetCompatibilityVersion(CompatibilityVersion.Version_2_2);
}
```

Both middleware are registered in the request processing pipeline in `Startup.Configure`:

```
public void Configure(IApplicationBuilder app, IHostingEnvironment env)
{
    if (env.IsDevelopment())
    {
        app.UseDeveloperExceptionPage();
        app.UseDatabaseErrorPage();
    }
    else
    {
        app.UseExceptionHandler("/Error");
    }

    app.UseConventionalMiddleware();
    app.UseFactoryActivatedMiddleware();

    app.UseStaticFiles();
    app.UseMvc();
}
```

## IMiddlewareFactory

[IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) provides methods to create middleware. The middleware factory implementation is registered in the container as a scoped service.

The default [IMiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.imiddlewarefactory) implementation, [MiddlewareFactory](/en-us/dotnet/api/microsoft.aspnetcore.http.middlewarefactory), is found in the [Microsoft.AspNetCore.Http](https://www.nuget.org/packages/Microsoft.AspNetCore.Http/) package.

## Additional resources

- [ASP.NET Core middleware](./?view=aspnetcore-10.0)
- [Middleware activation with a third-party container in ASP.NET Core](extensibility-third-party-container?view=aspnetcore-10.0)

---

## Additional resources

---

- Last updated on 
  2025-08-28
