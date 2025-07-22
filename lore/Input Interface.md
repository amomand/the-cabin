
## Hybrid Parser + Suggestion Model

  

### **Summary**

  

The Cabin will use a **hybrid input system**, combining structured options with a free-text parser. The system is designed to support atmosphere, allow creative expression, and gently guide the player — without going full AI chaos monkey.

---

### **Core Behaviour**

- At each game step, the player sees:
    
    - A **descriptive scene**
        
    - A list of **suggested actions** (2–4 options)
        
    - A **free input box** (“Or type your own…”)
        
    

---

### **Free-Text Parsing**

- Player may type any input.
    
- Game interprets this using a lightweight intent parser, looking for verb–noun structures.
    
- AI responses are:
    
    - **_Permissive_** if the intent is understood (even if there’s a typo)
        
    - **_Restrictive but in-universe_** if not understood or rejected (e.g. “You try, but the cold in your chest stops you.”)
        
    

  

### **Examples**

- opne door → auto-corrected to open door
    
- i levitate into the air and punch god → rejected with dry wit or in-universe snark
    
- talk to eli → valid if Eli is present
    
- run north → valid if north is a known/valid exit
    

---

### **Intent Matching**

- Use a fallback list of verbs/actions to compare with input:
    
    - Movement: go, walk, run, climb
        
    - Object interaction: open, close, take, drop, examine, light, extinguish
        
    - Social: talk, shout, whisper, listen
        
    - Survival: rest, eat, drink, hide, wait
        
    
- Typos are handled with fuzzy matching (Levenshtein distance or similar)
    

---

### **Suggested Actions**

- Each location provides curated choices, designed to:
    
    - Maintain pacing and narrative tone
        
    - Offer affordances for progression
        
    - Act as training wheels for less confident players
        
    
- Over time, suggested options may:
    
    - **Fade or reduce**, encouraging freeform input
        
    - **Shift in tone** (e.g. more ominous, sparse, or wrong…)
        
    

---

### **Re-evaluation Note**

  

This system is **deliberately open to change**.

- If future iterations show GPT-style inputs with stricter guidance and narrative rails can work, we may switch.
    
- A fallback hard-parser mode (e.g. verb–noun only) could also be supported.
    

---

### **Next Ideas To Explore**

- Command synonyms and aliasing (e.g. look = examine = inspect)
    
- Scene-specific verb whitelisting
    
- Adding “narrative AI override” moments — e.g. Lyer influence interferes with commands
    
- Integration with dynamic map updates based on explored routes
    

---

### **Notes for Dev Implementation**

- Use fuzzy string matching (e.g. Levenshtein distance < 2)
    
- Maintain a fallback intent parser with limited verb–noun pairs
    
- Flag invalid actions with tone-aware error responses
    
- Consider storing previous commands for context inference
    
- Suggested actions could be presented as buttons with on-hover tooltips
    

---

More to come as we define player state, inventory logic, and the fear/health system.