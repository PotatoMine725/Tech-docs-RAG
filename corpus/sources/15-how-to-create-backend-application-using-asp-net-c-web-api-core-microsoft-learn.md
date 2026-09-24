# How to create backend application using Asp.net C# Web API Core - Microsoft Learn

Source: https://learn.microsoft.com/en-gb/answers/questions/1679916/how-to-create-backend-application-using-asp-net-c

---

# How to create backend application using Asp.net C# Web API Core

![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(179.20000000000002, 39%, 27%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3ECR%3C/text%3E%3C/svg%3E)

[coder rock](/en-gb/users/na/?userid=5c6a39bc-b66b-4734-a95c-595a61192bb6)

436
Reputation points

2024-05-17T06:22:52.4166667+00:00

How to create backend application using web api core application followed by standards

using desing pattern, Depedency injection and solid principle

I am new to web api core how to start following things

1. JWT token authentical and authorization
2. simple role base login there will two roles 1)admin and 2)user

Developer technologies | C#

[Developer technologies | C#](/en-gb/answers/tags/823/developer-technologies-csharp/)

An object-oriented and type-safe programming language that has its roots in the C family of languages and includes support for component-oriented programming.

Developer technologies | ASP.NET Core | Other

[Developer technologies | ASP.NET Core | Other](/en-gb/answers/tags/1591/developer-technologies-aspnet-core-other-l1/)

A set of technologies in .NET for building web applications and web services. Miscellaneous topics that do not fit into specific categories.

0 comments
No comments

---

[Sign in to comment](#)

Answer accepted by question author

![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(128, 8%, 22%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3EA%3C/text%3E%3C/svg%3E)

Anonymous

2024-05-17T08:11:04.2133333+00:00

Hi @[coder rock](https://learn.microsoft.com/en-us/users/na/?userid=5c6a39bc-b66b-4734-a95c-595a61192bb6),

If you want to use JWT auth inside the web api, you need firstly install the jwt package:

```
Microsoft.AspNetCore.Authentication.JwtBearer
```

Then you could add the jwt auth related codes inside the program.cs and add app.UseAuthentication(); middleware:

Like below, if you want you could modify the Issuer, audience, signingkey by yourself:

```
var builder = WebApplication.CreateBuilder(args);
// Add services to the container.
builder.Services.AddControllers();
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = "your-issuer",
            ValidAudience = "your-audience",
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes("xxxxxxxassaaaaaaasdddxxxxxxxxxxxxxxxx"))
        };
    });
var app = builder.Build();
// Configure the HTTP request pipeline.
app.UseHttpsRedirection();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
app.Run();
```

Then inside the user controller we could generate the token and use that token to access the protected web api method.

Please notice: My sample doesn't contain the username and password verify, you could modify the codes to verify username and password based on the request body and then set the user role based on the username inside the GenerateJwtToken method.

```
    [Route("api/[controller]")]
    [ApiController]
    public class UserController : ControllerBase
    {

        [HttpPost("authenticate")]
        public async Task<IActionResult> Authenticate()
        {
            //Here you could pass user to generatejwttoeknmethod to generate the token based on the user
            var token = GenerateJwtToken( );
 
            if (token == null)
                return BadRequest(new { message = "Username or password is incorrect" });

            return Ok(token);
        }

        private string GenerateJwtToken( )
        {
            var tokenHandler = new JwtSecurityTokenHandler();
            var key = Encoding.ASCII.GetBytes("xxxxxxxassaaaaaaasdddxxxxxxxxxxxxxxxx");
            var tokenDescriptor = new SecurityTokenDescriptor
            {
                Subject = new ClaimsIdentity(new[] { new Claim("id", "testuser"), new Claim(ClaimTypes.Role, "Admin") }),
                Issuer = "your-issuer",
                Audience = "your-audience",
                Expires = DateTime.UtcNow.AddDays(7),
                SigningCredentials = new SigningCredentials(new SymmetricSecurityKey(key), SecurityAlgorithms.HmacSha256Signature)
            };
       
            var token = tokenHandler.CreateToken(tokenDescriptor);
            return tokenHandler.WriteToken(token);
        }

        public async Task<IActionResult> Register( )
        {
            return Ok();
        }

        [HttpGet]
        [Authorize(Roles = "Admin")]
        public async Task<IActionResult> GetAll()
        {
             
            return Ok("success");
        }
    }
```

Test Result:

Authencation:

![User's image](https://learn-attachment.microsoft.com/api/attachments/5c8530b9-ba6d-4633-b8e7-f439fa02b366?platform=QnA)

Access admin role api method:

![User's image](https://learn-attachment.microsoft.com/api/attachments/f2935202-fd6b-4ed0-a887-a57874028e59?platform=QnA)

If the answer is the right solution, please click "Accept Answer" and kindly upvote it. If you have extra questions about this answer, please click "Comment". Note: Please follow the steps in our [documentation](https://docs.microsoft.com/en-us/answers/support/email-notifications) to enable e-mail notifications if you want to receive the related email notification for this thread.

1. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(179.20000000000002, 39%, 27%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3ECR%3C/text%3E%3C/svg%3E)

   [coder rock](/en-gb/users/na/?userid=5c6a39bc-b66b-4734-a95c-595a61192bb6)

   •

   436
   Reputation points

   2024-05-17T08:35:52.61+00:00

   I have installed below version of jwt using console:

   NuGet\Install-Package Microsoft.AspNetCore.Authentication.JwtBearer -Version 5.0.5

   and latest version of jwt is not supporting with net5.0

   NU1202: Package Microsoft.AspNetCore.Authentication.JwtBearer 8.0.5 is not compatible with net5.0 (.NETCoreApp,Version=v5.0
2. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(128, 8%, 22%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3EA%3C/text%3E%3C/svg%3E)

   Anonymous

   2024-05-17T09:35:47.32+00:00

   .NET 5 is out of support, I suggest you use .net 8 instead of 5, you could download the SDK by using this url <https://dotnet.microsoft.com/en-us/download/dotnet/8.0>.
3. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(128, 8%, 22%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3EA%3C/text%3E%3C/svg%3E)

   Anonymous

   2024-05-20T02:13:19.64+00:00

   Hi @[coder rock](https://learn.microsoft.com/en-us/users/na/?userid=5c6a39bc-b66b-4734-a95c-595a61192bb6), the latest version for Microsoft.AspNetCore.Authentication.JwtBearer the is 5.0.17 as below image shows, it is deprecated, but it still could be used for testing,   
   as I said before, I suggest you could use newest version asp.net core 8 instead of 5 .![User's image](https://learn-attachment.microsoft.com/api/attachments/db79721a-13b9-4798-ae20-d2cfa037dd83?platform=QnA)
4. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(179.20000000000002, 39%, 27%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3ECR%3C/text%3E%3C/svg%3E)

   [coder rock](/en-gb/users/na/?userid=5c6a39bc-b66b-4734-a95c-595a61192bb6)

   •

   436
   Reputation points

   2024-05-22T19:06:46.2933333+00:00

   Hi Brando, i have installed .NET 8 and also added below code

   Program.cs

   ```
   using Microsoft.AspNetCore.Authentication.JwtBearer;
   using Microsoft.IdentityModel.Tokens;
   using System.Text;

   var builder = WebApplication.CreateBuilder(args);
   // Add services to the container.
   builder.Services.AddControllers();
   builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
       .AddJwtBearer(options =>
       {
           options.TokenValidationParameters = new TokenValidationParameters
           {
               ValidateIssuer = true,
               ValidateAudience = true,
               ValidateLifetime = true,
               ValidateIssuerSigningKey = true,
               ValidIssuer = "https://localhost:7054", //your-issuer  
               ValidAudience = "https://localhost:7054",
               IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes("0123456789"))
           };
       });
   var app = builder.Build();
   // Configure the HTTP request pipeline.
   app.UseHttpsRedirection();
   app.UseAuthentication();
   app.UseAuthorization();
   app.MapControllers();
   app.Run();
   ```

   UserController.cs

   ```
   using Microsoft.AspNetCore.Authorization;
   using Microsoft.AspNetCore.Mvc;
   using Microsoft.IdentityModel.Tokens;
   using System.IdentityModel.Tokens.Jwt;
   using System.Security.Claims;
   using System.Text;

   namespace coreapidotnet8.Controllers
   {
       [ApiController]
       [Route("[controller]")]
       public class UserController : ControllerBase
       {
           [HttpPost("authenticate")]
           public async Task<IActionResult> Authenticate()
           {
               //Here you could pass user to generatejwttoeknmethod to generate the token based on the user
               var token = GenerateJwtToken();

               if (token == null)
                   return BadRequest(new { message = "Username or password is incorrect" });

               return Ok(token);
           }

           private string GenerateJwtToken()
           {
               var tokenHandler = new JwtSecurityTokenHandler();
               var key = Encoding.ASCII.GetBytes("0123456789");
               var tokenDescriptor = new SecurityTokenDescriptor
               {
                   Subject = new ClaimsIdentity(new[] { new Claim("id", "testuser"), new Claim(ClaimTypes.Role, "Admin") }),
                   Issuer = "https://localhost:7054",
                   Audience = "https://localhost:7054",
                   Expires = DateTime.UtcNow.AddDays(7),
                   SigningCredentials = new SigningCredentials(new SymmetricSecurityKey(key), SecurityAlgorithms.HmacSha256Signature)
               };

               var token = tokenHandler.CreateToken(tokenDescriptor);
               return tokenHandler.WriteToken(token);
           }

           public async Task<IActionResult> Register()
           {
               return Ok();
           }

           [HttpGet]
           [Authorize(Roles = "Admin")]
           public async Task<IActionResult> GetAll()
           {

               return Ok("success");
           }
       }
   }
   ```

   output is coming 404 not found.. issuer and audience given localhost url and key given 0 to 9 and claimsidentitty kept yours only "id" and "testuser". I am not much aware of postman

   ![User's image](https://learn-attachment.microsoft.com/api/attachments/8643ef20-523c-4c9f-ab77-1d3a0fd92171?platform=QnA)
5. ![](https://learn.microsoft.com/api/profile-avatar-storage/images/MxBLrky2rESG0hes4GqOKQ.png?8D92C1)

   [AgaveJoe](/en-gb/users/na/?userid=ae4b1033-b64c-44ac-86d2-17ace06a8e29)

   •

   31,706
   Reputation points

   2024-05-22T20:06:20.3933333+00:00

   A 404 (Not Found) means the URL was not found or there is no data. The URL you entered in PostMan is /api/user/authenticate. However you did not specify "api" in the route. You have the following.

   ```
   [Route("[controller]")]
   ```

   Update the route if you want /api

   ```
   [Route("api/[controller]")]
   ```

   Otherwise remove "api" from the URL. Please see the routing in ASP.NET Core documentation.

   <https://learn.microsoft.com/en-us/aspnet/core/fundamentals/routing?view=aspnetcore-8.0>
6. Deleted

   This comment has been deleted due to a violation of our Code of Conduct. The comment was manually reported or identified through automated detection before action was taken. Please refer to our [Code of Conduct](https://aka.ms/msftqacodeconduct) for more information.
7. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(179.20000000000002, 39%, 27%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3ECR%3C/text%3E%3C/svg%3E)

   [coder rock](/en-gb/users/na/?userid=5c6a39bc-b66b-4734-a95c-595a61192bb6)

   •

   436
   Reputation points

   2024-05-23T13:34:00.23+00:00

   why signature is showing invalid

   And how to achieve and implement dynamically using logintable of sql datatable

   my logintable like below

   ```
   UserName                                      Password

   coder		                                   Pass1234
   ```

   ![User's image](https://learn-attachment.microsoft.com/api/attachments/778a9dd9-bdf0-46d9-b2f0-ca41784c5545?platform=QnA)
8. ![](https://learn.microsoft.com/api/profile-avatar-storage/images/MxBLrky2rESG0hes4GqOKQ.png?8D92C1)

   [AgaveJoe](/en-gb/users/na/?userid=ae4b1033-b64c-44ac-86d2-17ace06a8e29)

   •

   31,706
   Reputation points

   2024-05-23T15:29:54.2+00:00

   > why signature is showing invalid

   The jwt.io page needs the encryption algorithm and secret you used to sign the JWT in order to verify the signature.

   JWT is an open standard. You should click the "Learn more about JWT" button at the top of the page read the docs.
9. ![](data:image/svg+xml, %3Csvg xmlns='http://www.w3.org/2000/svg' height='64' class='font-weight-bold' style='font: 600 30.11764705882353px "SegoeUI", Arial' width='64'%3E%3Ccircle fill='hsl(179.20000000000002, 39%, 27%)' cx='32' cy='32' r='32' /%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23FFF' %3ECR%3C/text%3E%3C/svg%3E)

   [coder rock](/en-gb/users/na/?userid=5c6a39bc-b66b-4734-a95c-595a61192bb6)

   •

   436
   Reputation points

   2024-05-25T08:59:24.57+00:00

   Great and thanks for support,

   Now API is working fine but my requiremnt is different,

   I have to do with sql table like my table name is logindetails have columns emailid and password,

   how to achieve login functionality using emailid and paswword
10. ![](https://learn.microsoft.com/api/profile-avatar-storage/images/MxBLrky2rESG0hes4GqOKQ.png?8D92C1)

    [AgaveJoe](/en-gb/users/na/?userid=ae4b1033-b64c-44ac-86d2-17ace06a8e29)

    •

    31,706
    Reputation points

    2024-05-25T11:01:50.8366667+00:00

    > I have to do with sql table like my table name is logindetails have columns emailid and password, how to achieve login functionality using emailid and paswword

    I assume you are very new to ASP.NET Core.

    There are several pieces to your question. One is setting up data access. I assume you want to use Entity Framework. The following tutorial illustrates all the steps to register Entity Framework with the dependency injection framework in an MVC application. Setting up DI in MVC is identical to Web API.

    <https://learn.microsoft.com/en-us/aspnet/core/data/ef-mvc/intro?view=aspnetcore-8.0>

    Here's a tutorial for Web API. the MVC tutorial is a bit more in dept.

    <https://learn.microsoft.com/en-us/training/modules/build-web-api-aspnet-core/?view=aspnetcore-8.0>

    Once you Entity Framework working then you'll need to inject the Db Context into the Authenticate controller's constructor.

    You also update the authenticate action to accept a login model which will contain the emailid and password. Finally, you'll write a LINQ expression to query the logindetails table by the emailid and password.

    Keep in mind, this is the 4th question in the same post. Create a new post if you run into trouble.

---

[Sign in to comment](#)

## 0 additional answers

Sort by:
Most helpful

[Most helpful](?orderby=helpful&page=1#answers) [Newest](?orderby=newest&page=1#answers) [Oldest](?orderby=oldest&page=1#answers)

[Sign in to answer](#)

## Your answer
