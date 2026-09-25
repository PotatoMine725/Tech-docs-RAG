# Querying Data - EF Core - Microsoft Learn

Source: https://learn.microsoft.com/en-us/ef/core/querying/

---

---

Note

Access to this page requires authorization. You can try [signing in](#) or changing directories.

Access to this page requires authorization. You can try changing directories.

# Querying Data

Entity Framework Core uses Language-Integrated Query (LINQ) to query data from the database. LINQ allows you to use C# (or your .NET language of choice) to write strongly typed queries. It uses your derived context and entity classes to reference database objects. EF Core passes a representation of the LINQ query to the database provider. Database providers in turn translate it to database-specific query language (for example, SQL for a relational database). Queries are always executed against the database even if the entities returned in the result already exist in the context.

Tip

You can view this article's [sample](https://github.com/dotnet/EntityFramework.Docs/tree/main/samples/core/Querying/Overview) on GitHub.

The following snippets show a few examples of how to achieve common tasks with Entity Framework Core.

## Loading all data

```
using (var context = new BloggingContext())
{
    var blogs = await context.Blogs.ToListAsync();
}
```

## Loading a single entity

```
using (var context = new BloggingContext())
{
    var blog = await context.Blogs
        .SingleAsync(b => b.BlogId == 1);
}
```

## Filtering

```
using (var context = new BloggingContext())
{
    var blogs = await context.Blogs
        .Where(b => b.Url.Contains("dotnet"))
        .ToListAsync();
}
```

## Further readings

- Learn more about [LINQ query expressions](/en-us/dotnet/csharp/programming-guide/concepts/linq/basic-linq-query-operations)
- For more detailed information on how a query is processed in EF Core, see [How queries Work](how-query-works).

---

## Additional resources

---

- Last updated on 
  2021-03-11
