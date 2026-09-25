# Sharing services added with dependencies via the basic view - Microsoft Q&A

Source: https://learn.microsoft.com/en-gb/answers/questions/1512035/sharing-services-added-with-dependencies-via-the-b

---

# Sharing services added with dependencies via the basic view

![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(112.00000000000001, 17%, 20%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3EFU%3C/text%3E%3C/svg%3E)

[fatih uyanık](/en-gb/users/na/?userid=ff35174a-1a57-4578-943a-ad989b4f9fba)

245
Reputation points

2024-01-25T13:31:57.54+00:00

Hello
With injection I currently have 3 services and I use them on view models. Instead of defining these models individually within each view model, I defined them in the base view model. Then I try to use it wherever I want. The problem is: I need to send them as parameters one by one in each view model's constructor method. I chose this method to avoid code repetition. But now the problem of sending it as a parameter has arisen. Can you help me with this?
Thanks.

Developer technologies | Windows Presentation Foundation

[Developer technologies | Windows Presentation Foundation](/en-gb/answers/tags/147/developer-technologies-windows-wpf/)

A part of the .NET Framework that provides a unified programming model for building line-of-business desktop applications on Windows.

Developer technologies | C#

[Developer technologies | C#](/en-gb/answers/tags/823/developer-technologies-csharp/)

An object-oriented and type-safe programming language that has its roots in the C family of languages and includes support for component-oriented programming.

1. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(128, 8%, 22%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3EA%3C/text%3E%3C/svg%3E)

   Anonymous

   2024-01-26T08:40:59.43+00:00

   Hi @[fatih uyanık](https://learn.microsoft.com/en-us/users/na/?userid=ff35174a-1a57-4578-943a-ad989b4f9fba) , Welcome to Microsoft Q&A,
   What projects are you currently creating? The ASP.NET Core framework provides a built-in dependency injection container. Here is the official example:<https://learn.microsoft.com/en-us/aspnet/core/fundamentals/dependency-injection?view=aspnetcore-8.0>
2. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(112.00000000000001, 17%, 20%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3EFU%3C/text%3E%3C/svg%3E)

   [fatih uyanık](/en-gb/users/na/?userid=ff35174a-1a57-4578-943a-ad989b4f9fba)

   •

   245
   Reputation points

   2024-01-29T07:27:38.86+00:00

   Hello
   I am currently creating a wpf project. According to the MVVm pattern, my goal is to basically define and use the codes I use in each view model without falling into code repetition. For this, I basically defined the commands as features. But I am having problems applying the services I added with DI to the view models. I would be happy if you could support me on these issues.
   Thanks.

---

[Sign in to comment](#)

## 2 answers

Sort by:
Most helpful

[Most helpful](?orderby=helpful&page=1#answers) [Newest](?orderby=newest&page=1#answers) [Oldest](?orderby=oldest&page=1#answers)

1. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(291.2, 11%, 38%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3EHL%3C/text%3E%3C/svg%3E)

   [Hui Liu-MSFT](/en-gb/users/na/?userid=ad9fe1c1-ef13-44e4-842c-101fe0f5b146)

   •

   48,721
   Reputation points • Microsoft External Staff

   2024-01-29T09:34:25.3933333+00:00

   Hi,@[fatih uyanık](https://learn.microsoft.com/en-us/users/na/?userid=ff35174a-1a57-4578-943a-ad989b4f9fba).Welcome Microsoft Q&A.

   For the issue about avoiding code repetition by defining common services in a base view model and then using dependency injection to provide those services to various view models. However, you are facing challenges in passing these services as parameters to the constructor of each view model.

   Here are a few approaches you could consider:

   **Dependency Injection Container:**
   Instead of manually passing services as parameters to each view model constructor, consider using a dependency injection (DI) container, such as Microsoft's Dependency Injection container.
   Register your services in the DI container during application startup.
   Resolve and inject these services into your view models automatically.

   Example with Microsoft.Extensions.DependencyInjection:

   ```
   // Startup.cs
   public void ConfigureServices(IServiceCollection services)
   {
       services.AddScoped<IMyService, MyService>();
       // Register other services
   }

   // YourViewModel.cs
   public YourViewModel(IMyService myService)
   {
       // Use myService in your view model
   }
   ```

   **BaseViewModel Initialization:**
   Instead of passing services individually to each view model constructor, consider having a centralized method in your BaseViewModel that initializes the required services.
   Each view model calls this method during its initialization.
   Example:

   ```
   public class BaseViewModel
   {
       protected IService1 Service1 { get; private set; }
       protected IService2 Service2 { get; private set; }

       protected void InitializeServices(IService1 service1, IService2 service2)
       {
           Service1 = service1;
           Service2 = service2;
       }
   }

   public class YourViewModel : BaseViewModel
   {
       public YourViewModel(IService1 service1, IService2 service2)
       {
           InitializeServices(service1, service2);
           // Use Service1 and Service2 in your view model
       }
   }
   ```

   Choose the approach that best fits your application structure and requirements. Using a DI container is generally considered a good practice for managing dependencies in a clean and modular way.

   ---

   If the answer is the right solution, please click "Accept Answer" and kindly upvote it. If you have extra questions about this answer, please click "Comment".
   **Note:** Please follow the steps in our [documentation](https://docs.microsoft.com/en-us/answers/articles/67444/email-notifications.html) to enable e-mail notifications if you want to receive the related email notification for this thread.

   1. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(112.00000000000001, 17%, 20%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3EFU%3C/text%3E%3C/svg%3E)

      [fatih uyanık](/en-gb/users/na/?userid=ff35174a-1a57-4578-943a-ad989b4f9fba)

      •

      245
      Reputation points

      2024-01-29T10:11:02.7733333+00:00

      Hello
      Firstly, thank you. Some things occurred in my mind. After defining the services I use in the view models in the base view model, I send them via the constructor method in each view model. Well, while doing this, I do not want to send the service that I will not use in the current view model as a parameter. How can I do that? Optionally to start? However, I don't know if it is correct to define services in the basic view model.
      Thanks.
   2. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(291.2, 11%, 38%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3EHL%3C/text%3E%3C/svg%3E)

      [Hui Liu-MSFT](/en-gb/users/na/?userid=ad9fe1c1-ef13-44e4-842c-101fe0f5b146)

      •

      48,721
      Reputation points • Microsoft External Staff

      2024-01-30T02:32:03.3566667+00:00

      Hi,@[fatih uyanık](https://learn.microsoft.com/en-us/users/na/?userid=ff35174a-1a57-4578-943a-ad989b4f9fba). When you have a service defined in a base view model and want to pass the services that a specific view model requires, you could try to refer to the following strategy.   
      **Define Optional Services:**

      In your base view model, define the services as properties, and make the properties nullable if the services are optional.
      Example:

      ```
      public class BaseViewModel
      {
          protected IService1? Service1 { get; private set; }
          protected IService2? Service2 { get; private set; }
          
          public void SetService1(IService1 service)
          {
              Service1 = service;
          }

          public void SetService2(IService2 service)
          {
              Service2 = service;
          }
      }
      ```

      Individual View Models:
      In your individual view models, call the corresponding SetServiceX method to set the services you need.

      ```
      public class YourViewModel : BaseViewModel
      {
          public YourViewModel(IService1 service1)
          {
              SetService1(service1);
              // Use Service1 in your view model
          }
      }
      ```

      **Lazy Initialization:**

      Instead of initializing services in the base view model's constructor, consider lazy initialization.
      Initialize services only when they are first requested by a view model.

      Example:

      ```
      public class BaseViewModel
      {
          private IServiceA _serviceA;
          private IServiceB _serviceB;

          protected IServiceA ServiceA => _serviceA ??= new ServiceA();
          protected IServiceB ServiceB => _serviceB ??= new ServiceB();
      }

      public class YourViewModel : BaseViewModel
      {
          public YourViewModel()
          {
              // ServiceA and ServiceB are initialized when first accessed
          }
      }
      ```

      Choose the approach that best fits your application's structure and requirements.

   ---

   [Sign in to comment](#)
2. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(211.20000000000002, 61%, 30%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3EBS%3C/text%3E%3C/svg%3E)

   [Bruce (SqlWork.com)](/en-gb/users/na/?userid=6f6bb61e-afe6-4f38-9f92-62a4655b7267)

   •

   85,451
   Reputation points

   2024-01-25T16:17:16.54+00:00

   DI uses the constructor to pass the injected objects. The .net runtime does not support constructor inheritance, so you need to define an injection constructor for each view model. Your base class can have a common constructor that is called.

   `public MyModel(MyDI1 di1) : base(di)`

   1. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(112.00000000000001, 17%, 20%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3EFU%3C/text%3E%3C/svg%3E)

      [fatih uyanık](/en-gb/users/na/?userid=ff35174a-1a57-4578-943a-ad989b4f9fba)

      •

      245
      Reputation points

      2024-01-25T19:20:34.54+00:00

      Hello
      Firstly, thank you. Can you share an example structure with me?

   ---

   [Sign in to comment](#)

[Sign in to answer](#)

## Your answer
