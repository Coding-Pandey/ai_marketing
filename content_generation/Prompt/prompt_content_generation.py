blog_prompt = """
Write a comprehensive blog post using the provided copy and external link sources.
The article must integrate external information along with internal factors such as tone of voice, brand identity,
and target personas. 

- **Tone of Voice Guidelines**:
  {Tone}
- **Target Buyer Persona Guidelines**:
  {Buyer}
- **Brand Identity Guidelines**:
  {Brand}
- **Offering Guidelines**:
  {Offering}

**Requirements for the Article**:

1.**Introduction**:
    - Begin with an attention-grabbing hook between 50 and 70 words.
    - Set the context by explaining why the topic is important without using phrases like "this guide" or "in this article".

2.**Structure**:
    - Use clear subheadings or sections that outline the main arguments or points.
    - Include sections that provide:
        - Problem Overview and Implications: Clearly describe the problem, idea, or recent news that prompted interest in this topic. Explain the potential threats it poses or the opportunities it creates, and hint at viable solutions or strategies.
        - Key Points or Arguments: Present your arguments with relevant examples, data, quotes, or short case studies.
        - Data, Evidence, or Expert Opinions: Incorporate statistics, industry reports, expert quotes, and visual support where applicable. Place links to these sources as anchor text when the information is used.
        - Counterarguments or Common Misconceptions: Address alternative viewpoints and offer evidence-based rebuttals.
        - Actionable Steps or Best Practices: Present this in paragraphs with headlines that may have rider numbers such as 1., 2., 3., etc.

3.**Conclusion**:
    - Instead of a standard conclusion paragraph, create a clever title that summaries the key takeaways that reader may apply or consider.
    - Ensure the conclusion reinforces the core argument with a succinct, actionable summary that readers can apply in real life.

4.**Formatting and Style**:
    - Use inline styling with the provided tone of voice.
    - Write the article in a way that is interesting and relevant for the target personas, in a style that resonates with them.
    - Avoid using hyphens anywhere in the article.
    - Aim for an overall length between 2000 and 2800 words.

5.**Additional Guidelines**:
    - Integrate both external data and internal insights (tone of voice, brand identity, target personas) to create a rich and engaging narrative.
    -  Ensure a compelling flow from start to finish with clear transitions between sections.


**Output**   
In json object with single dict have key value pare 
- Title: A short, catchy phrase or question that captures the essence of the article and the attention
- Topic: A concise title that incorporates target keywords and is optimised for search engines.
- description: A brief, engaging summary of the article designed for SEO purposes.
- Introduction: A small, to the point summary that provides an overview of the content.
- Section's: Give multi section based on artical topic , Not giving topic on section just highlite Topic or main point
- conclusion: only give single content

blog content
{items}
"""

new_promt ="""
Write a comprehensive blog post using the provided copy and external link sources.
The article must integrate external information with internal factors such as tone of voice, brand identity, and target personas.

**Tone of Voice Guidelines**:
{Tone}
**Target Buyer Persona Guidelines**:
{Buyer}
**Brand Identity Guidelines**:
{Brand}
**Offering Guidelines**:
{Offering}

**Requirements for the Article**:
    - Introduction:
        Start with an attention-grabbing hook between 50 and 70 words.
        Set the context by explaining the topic’s importance without using phrases like "this guide" or "in this article".
    - Structure:
        Use clear subheadings to outline the main arguments or points.
        Include the following sections:
        Problem Overview and Implications: Clearly describe the problem, idea, or recent news driving interest in this topic. Explain its potential threats or opportunities and hint at viable solutions or strategies.
        Key Points or Arguments: Present arguments supported by relevant examples, data, quotes, or short case studies.
        Data, Evidence, or Expert Opinions: Incorporate statistics, industry reports, expert quotes, and visual support where applicable. Embed links to sources as anchor text when the information is used.
        Counterarguments or Common Misconceptions: Address alternative viewpoints and provide evidence-based rebuttals.
        Actionable Steps or Best Practices: Offer practical advice in paragraphs with numbered subheadings (e.g., 1., 2., 3.) for clarity.
    - Conclusion:
        Replace a standard conclusion paragraph with a clever title that summarizes key takeaways for readers to apply or consider.
        Reinforce the core argument with a succinct, actionable summary applicable to real life.
    - Formatting and Style:
        Apply inline styling consistent with the provided tone of voice.
        Tailor the article to be engaging and relevant for the target personas, using a style that resonates with them.
        Avoid hyphens throughout the article.
        Target an overall length of 2000 to 2800 words.
    - Additional Guidelines:
        Blend external data and internal insights (tone of voice, brand identity, target personas) into a rich, engaging narrative.
        Ensure a compelling flow from start to finish with smooth transitions between sections.

**Output**:

Return a JSON object with a single dictionary containing the following key-value pairs:
    - Title: A short, catchy phrase or question that captures the article’s essence and grabs attention. A concise title incorporating target keywords, optimized for search engines.
    - Description: A brief, engaging summary of the article designed for SEO purposes.
    - Introduction: A concise summary providing an overview of the content, aligned with the hook and context.
    - Sections: An array of section objects, each representing a main point or argument. Each object should include:
    - Subheading: A clear, descriptive title for the section (e.g., "Problem Overview and Implications").
    - Content: - Detailed text for the section, written in paragraphs, incorporating the specified requirements (e.g., data, examples, actionable steps).
               - Do not include a "topic" field within sections; focus on the subheading and content to highlight the main point.
    - Conclusion: A single string containing the clever title and actionable summary.

blog content
{items}

"""

summary = {
  "Tone of Voice Guidelines": [
    "Authoritative & Trustworthy: Use clear, evidence-based language backed by scientific research.",
    "Reassuring & Empathetic: Address patient anxiety and emphasize non-invasive procedures to create a compassionate tone.",
    "Innovative & Forward-Looking: Highlight cutting-edge technology and future potential for early cancer detection.",
    "Accessible & Clear: Communicate in plain language, avoiding jargon while ensuring understanding.",
    "Regular updates: Keep messaging relevant by aligning with recent clinical data and developments."
  ],
  "Target Buyer Persona Guidelines": [
    "Proactive Patricia – The Health-Conscious Professional: Values early detection and seeks non-invasive screening options.",
    "Dr. David – The Forward-Thinking Physician: Focuses on reliable testing methods and clinically validated research.",
    "Skeptical Sam – The Health Insurance/Clinic Decision Maker: Aims to reduce healthcare costs and requires strong data to validate decisions.",
    "Common traits include a commitment to preventative care, detailed research needs, and concern for cost-effectiveness.",
    "Communication preferences vary from data-driven, clear messaging to concise executive summaries."
  ],
  "Services and Offerings Guidelines": [
    "Colosafe Darmkrebsfrüherkennungstest: A non-invasive cancer detection test with 99% accuracy, aimed at patients seeking early diagnosis.",
    "13-in-1 PCR: A multiplex PCR assay that detects 13 targets simultaneously for efficient diagnostics.",
    "Key marketing points highlight rapid results, non-invasiveness, and endorsements from leading oncologists.",
    "Each product is positioned to enhance patient outcomes and offers cost efficiency by reducing the need for traditional invasive procedures.",
    "Ongoing innovation and digital integration are emphasized to ensure accessibility and a seamless testing experience."
  ],
  "Brand Identity Guidelines": [
    "Market Leader in Diagnostic Innovation: Position as a pioneer in colon cancer testing through scientific excellence.",
    "Patient Empowerment: Focus on providing reliable, non-invasive tools that foster proactive health management.",
    "Trusted by Medical Experts: Build credibility through endorsements and robust clinical validation.",
    "Future-Forward: Vision of broader adoption and continuous innovation to improve access and sustainability.",
    "All branding elements emphasize emotional connection, scientific rigor, and ongoing engagement with patients and healthcare providers."
  ]
}
