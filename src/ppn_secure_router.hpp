#pragma once

#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <regex>

namespace alluci {

struct CloudRoutingManifest {
    std::string clean_abstract_payload;
    std::map<std::string, std::string> pii_vault_registry; // Maps abstracted token back to original PII
};

class AlluciSovereignRouter {
private:
    // Internal patterns to capture names, emails, credentials, and financial metrics
    std::vector<std::pair<std::string, std::regex>> pii_scrub_rules = {
        {"EMAIL", std::regex(R"([\w\.-]+@[\w\.-]+\.\w+)")},
        {"SSN", std::regex(R"(\b\d{3}-\d{2}-\d{4}\b)")},
        {"CREDIT_CARD", std::regex(R"(\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b)")},
        {"PHONE", std::regex(R"(\b\d{3}[-.]?\d{3}[-.]?\d{4}\b)")}
    };

public:
    AlluciSovereignRouter() {
        std::cout << "[C++ Proxy] Sovereign Router Initialized. Privacy Perimeter Active." << std::endl;
    }

    // Step 1: Structural Scrubbing and Data Isolating Pass
    CloudRoutingManifest isolate_personal_perimeter(const std::string& raw_user_prompt) {
        CloudRoutingManifest manifest;
        std::string mutated_buffer = raw_user_prompt;
        int token_counter = 0;

        for (const auto& rule_pair : pii_scrub_rules) {
            const std::string& token_type = rule_pair.first;
            const std::regex& rule = rule_pair.second;
            
            std::smatch match;
            std::string temp_buffer = mutated_buffer;
            mutated_buffer = "";
            
            auto search_start = temp_buffer.cbegin();
            while (std::regex_search(search_start, temp_buffer.cend(), match, rule)) {
                // Append the prefix string
                mutated_buffer += match.prefix().str();
                
                // Generate a unique anonymized token
                std::string secure_token = "[ANON_" + token_type + "_" + std::to_string(token_counter++) + "]";
                
                // Store the mapping securely in local memory
                manifest.pii_vault_registry[secure_token] = match.str(0);
                
                // Insert the safe token into the payload
                mutated_buffer += secure_token;
                
                // Move the search pointer forward
                search_start = match.suffix().first;
            }
            // Append the remaining suffix
            mutated_buffer += std::string(search_start, temp_buffer.cend());
        }

        manifest.clean_abstract_payload = mutated_buffer;
        return manifest;
    }

    // Step 2: Re-inject PII into the cloud response
    std::string deanonymize_response(const std::string& cloud_response, const std::map<std::string, std::string>& pii_vault_registry) {
        std::string final_response = cloud_response;
        
        // Reverse replace all safe tokens with the original PII securely
        for (const auto& pair : pii_vault_registry) {
            size_t pos = 0;
            while ((pos = final_response.find(pair.first, pos)) != std::string::npos) {
                final_response.replace(pos, pair.first.length(), pair.second);
                pos += pair.second.length();
            }
        }
        
        return final_response;
    }
};

} // namespace alluci
