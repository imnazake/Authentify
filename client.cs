using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading.Tasks;
using System.Text.Json;

namespace TestClient
{
    class Program
    {
        // Your API endpoint and API key
        private static readonly string ApiUrl = "http://localhost:5000/auth"; // Change if needed
        private static readonly string ApiKey = "your-secure-api-key";
        private static string generatedHwId;

        static async Task Main(string[] args)
        {
            // Call your function that creates or generate a hwid from the local machine
            generatedHwId = GetHWID();
            
            Console.WriteLine("Enter your license key:");
            string licenseKey = Console.ReadLine();
            
            var result = await AuthenticateKeyAsync(licenseKey, generatedHwId);

            Console.WriteLine("\nServer Response:");
            Console.WriteLine($"Status: {result.status}");
            if (!string.IsNullOrEmpty(result.message))
                Console.WriteLine($"Message: {result.message}");
        }

        public static async Task<(string status, string message)> AuthenticateKeyAsync(string key, string hwid)
        {
            using HttpClient client = new HttpClient();

            // Set API Key Header
            client.DefaultRequestHeaders.Add("X-API-Key", ApiKey);

            // Prepare JSON payload
            var payload = new
            {
                key = key,
                hwid = hwid
            };

            var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");

            try
            {
                HttpResponseMessage response = await client.PostAsync(ApiUrl, content);
                string jsonResponse = await response.Content.ReadAsStringAsync();

                using JsonDocument doc = JsonDocument.Parse(jsonResponse);
                var root = doc.RootElement;

                string status = root.GetProperty("status").GetString();
                string message = root.TryGetProperty("message", out var msgElement) ? msgElement.GetString() : null;

                return (status, message);
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine("Error connecting to the server: " + ex.Message);
                return ("error", "could not reach server");
            }
        }
    }
}
