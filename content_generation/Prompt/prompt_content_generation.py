blog_prompt = """
Write a comprehensive blog post using the provided copy and external link sources.
The article must integrate external information along with internal factors such as tone of voice, brand identity,
and target personas. The tone should be confident, engaging, and occasionally provocative. 
It must also maintain a conversational style that encourages readers to think deeply and consider different arguments.

Before the main article, include the following elements at the top of the output:
    1. A headline: A short, catchy phrase or question that captures the essence of the article and the attention
    2. An SEO friendly page title: A concise title that incorporates target keywords and is optimised for search engines.
    3. A meta description: A brief, engaging summary of the article designed for SEO purposes.
    4. A short, engaging article intro: A small, to the point summary that provides an overview of the content.

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
"""