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

            if (result.status == "ok")
            {
                 Console.WriteLine("✅ Authentication successful. Proceeding...");
                 // TODO: Launch main application or features
            }
            else
            {
                 Console.WriteLine("❌ Authentication failed. Exiting...");
            }
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
        
                switch ((int)response.StatusCode)
                {
                    case 200:
                        // Expect success message in JSON (e.g., "HWID linked" or "HWID verified")
                        using (JsonDocument doc = JsonDocument.Parse(jsonResponse))
                        {
                            string message = doc.RootElement.GetProperty("detail").GetString();
                            return ("ok", message);
                        }
        
                    case 401:
                        return ("unauthorized", "Invalid API key.");
        
                    case 403:
                        return ("expired", "Key has expired.");
        
                    case 404:
                        return ("invalid", "Invalid key.");
        
                    case 409:
                        return ("hwid_mismatch", "HWID mismatch.");
        
                    default:
                        return ("error", $"Unexpected error: {response.StatusCode} - {jsonResponse}");
                }
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine("Error connecting to the server: " + ex.Message);
                return ("error", "Could not reach the server.");
            }
        }

       
    }
}
