using Microsoft.Win32;
using System.Management;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

class APIResponse
{
    public string message { get; set; }
    public string data { get; set; }
}

class APITokenRequest
{
    public string username { get; set; }
    public string password { get; set; }
}

class APIActivateRequest
{
    public string hardware_spec1 { get; set; }
    public string hardware_spec2 { get; set; }
    public string hardware_spec3 { get; set; }
    public string hardware_spec4 { get; set; }
    public string hardware_spec5 { get; set; }
    public string license_key { get; set; }
}

class Program
{
    private static HttpClientHandler handler = new HttpClientHandler();
    private static readonly HttpClient client = new HttpClient(handler);

    private static readonly string publicKeyPem = @"---- INSERT YOUR PUBLIC KEY FROM THE API CONFIG HERE ----";

    private static string[] GetHardwareInfoArray()
    {
        string biosSerialNumber = "";
        using (var searcher = new ManagementObjectSearcher("SELECT SerialNumber FROM Win32_BIOS"))
        {
            foreach (ManagementObject obj in searcher.Get())
            {
                biosSerialNumber = obj["SerialNumber"]?.ToString();
            }
        }

        const string registryPath = @"SOFTWARE\Microsoft\Cryptography";
        const string valueName = "MachineGuid";
        string machineGuid = "";

        using (RegistryKey key = Registry.LocalMachine.OpenSubKey(registryPath))
        {
            if (key != null)
            {
                machineGuid = key.GetValue(valueName).ToString();
            }
        }

        string processorId = "";
        using (var searcher = new ManagementObjectSearcher("SELECT ProcessorId FROM Win32_Processor"))
        {
            foreach (ManagementObject obj in searcher.Get())
            {
                processorId = obj["ProcessorId"]?.ToString();
            }
        }

        return [biosSerialNumber, machineGuid, processorId, "", ""];
    }

    private static string GetHardwareId(string[] hardwareInfoArray)
    {
        string hardwareId = $"{hardwareInfoArray[0]}|{hardwareInfoArray[1]}|{hardwareInfoArray[2]}|{hardwareInfoArray[3]}|{hardwareInfoArray[4]}";
        return Convert.ToBase64String(Encoding.UTF8.GetBytes(hardwareId));
    }

    private static bool VerifyLicense()
    {
        string license = File.ReadAllText(".license");
        string licenseKey = File.ReadAllText(".licenseKey");

        byte[] decodedLicense = Convert.FromBase64String(license);

        string[] hardwareInfo = GetHardwareInfoArray();
        string dataToVerify = GetHardwareId(hardwareInfo) + licenseKey;

        byte[] data = Encoding.UTF8.GetBytes(dataToVerify);

        var rsa = RSA.Create();
        rsa.ImportFromPem(publicKeyPem);

        return rsa.VerifyData(data, decodedLicense, HashAlgorithmName.SHA256, RSASignaturePadding.Pss);
    }

    private static async Task CreateLicense()
    {
        try
        {
            var healthCheck = await client.GetAsync("https://localhost:5000");
            healthCheck.EnsureSuccessStatusCode();
        }
        catch
        {
            Console.WriteLine("API can't be reached.");
            Environment.Exit(0);
        }

        if (File.Exists(".license"))
            File.Delete(".license");

        if (File.Exists(".licenseKey"))
            File.Delete(".licenseKey");

        Console.WriteLine("Provide a license key:");
        string licenseKey = Console.ReadLine();

        Console.WriteLine("Provide your username:");
        string username = Console.ReadLine();

        Console.WriteLine("Provide your password:");
        string password = Console.ReadLine();

        APITokenRequest tokenRequest = new APITokenRequest()
        {
            username = username,
            password = password\
        };

        var content = new StringContent(JsonSerializer.Serialize(tokenRequest), Encoding.UTF8, "application/json");
        var response = await client.PostAsync("https://localhost:5000/auth", content);
        var responseString = await response.Content.ReadAsStringAsync();

        APIResponse responseObject = JsonSerializer.Deserialize<APIResponse>(responseString);
        string token = responseObject.data;

        string[] hardwareInfo = GetHardwareInfoArray();

        APIActivateRequest activateRequest = new APIActivateRequest()
        {
            hardware_spec1 = hardwareInfo[0],
            hardware_spec2 = hardwareInfo[1],
            hardware_spec3 = hardwareInfo[2],
            hardware_spec4 = hardwareInfo[3],
            hardware_spec5 = hardwareInfo[4],
            license_key = licenseKey
        };

        var request = new HttpRequestMessage(HttpMethod.Post, "https://localhost:5000/activate");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        request.Content = new StringContent(JsonSerializer.Serialize(activateRequest), Encoding.UTF8, "application/json");
        response = await client.SendAsync(request);
        responseString = await response.Content.ReadAsStringAsync();

        responseObject = JsonSerializer.Deserialize<APIResponse>(responseString);
        string license = responseObject.data;

        File.WriteAllText(".license", license);
        File.WriteAllText(".licenseKey", licenseKey);

        Console.WriteLine("Software was activated.");
        Environment.Exit(0);
    }

    static async Task Main(string[] args)
    {
        // Testing environment workaround - DO NOT USE IN PRODUCTION
        handler.ServerCertificateCustomValidationCallback = (sender, cert, chain, sslPolicyErrors) => { return true; };
        //

        Console.WriteLine("This is a demo licensed app for testing the software licensing API.\n");

        if (File.Exists(".license") && File.Exists(".licenseKey"))
        {
            if (VerifyLicense())
            {
                Console.WriteLine("This software is activated.");
            }
            else
            {
                Console.WriteLine("License is not valid.");
            }
            Console.WriteLine("You can try activating again by removing .license and .licenseKey files.");
            Console.ReadKey();
        }
        else
        {
            await CreateLicense();
            Console.ReadKey();
        }
    }
}