# Sample data for each city including total stars received and breakdown by voter city



candidates = {
    "Nashville": {"total_stars": 261, "from": {"Memphis": 84, "Nashville": 130, "Chattanooga": 39, "Knoxville": 8}},
    "Chattanooga": {"total_stars": 246, "from": {"Memphis": 42, "Nashville": 78, "Chattanooga": 150, "Knoxville": 51}},
    "Memphis": {"total_stars": 210, "from": {"Memphis": 210, "Nashville": 0, "Chattanooga": 0, "Knoxville": 0}},
    "Knoxville": {"total_stars": 182, "from": {"Memphis": 0, "Nashville": 52, "Chattanooga": 45, "Knoxville": 85}},
}

# Total stars to be displayed next to each candidate
total_display_stars = 50
nashville_total_stars = 261
scale = 26 / nashville_total_stars  # Adjust scale here for 26 colored stars for Nashville's 261 total stars

def assign_scaled_stars(candidates):
    # Apply the scale to determine the number of colored stars for each candidate
    for candidate, data in candidates.items():
        # Calculate colored stars based on the scale determined by Nashville's score
        colored_stars = round(data["total_stars"] * scale)
        
        # Calculate the proportion of colored stars from each city
        city_colored_stars = {city: round((stars / data["total_stars"]) * colored_stars) 
                              for city, stars in data["from"].items() if data["total_stars"] > 0}
        
        candidates[candidate]["colored_stars"] = colored_stars
        candidates[candidate]["city_colored_stars"] = city_colored_stars
    
    return candidates

# Apply the adjusted algorithm
updated_candidates_scaled = assign_scaled_stars(candidates)

# Example output with the adjusted scale
for candidate, data in updated_candidates_scaled.items():
    print(candidate, data["colored_stars"], data["city_colored_stars"])
