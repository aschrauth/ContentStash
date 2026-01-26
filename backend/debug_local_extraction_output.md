Dear subscribers,

Today, I want to share an extremely practical guide on AI evaluations.

> **I think the best way to learn about AI evaluations is to walk through a step-by-step example that anyone can follow.**

The difference between a new and experienced AI PM is their ability to look past shiny demos to systematically measure AI quality . So let’s cover:

1. Why AI evaluations matter
2. **Programmatic evals** to catch obvious failures
3. **Human evals** to label your golden dataset
4. **LLM judge evals** to scale
5. **User evals** to test with real customers

I also created a video tutorial with my friend [Aman](https://www.linkedin.com/in/amanberkeley/) where we demo building evals from scratch following the process above.

[Watch now](https://www.youtube.com/watch?v=TL527yTpxlk)

---

This post is brought to you by…**[Framer](https://framer.link/PeterYang)**

[![](https://substackcdn.com/image/fetch/$s_!T7-U!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F41642996-3f00-4b58-b8b4-8b53346d1fde_1456x764.png)](https://framer.link/PeterYang)

Some of the cleanest and fastest websites like Perplexity and Superhuman were built on Framer. It feels like designing in Figma with the power of shipping production-ready sites with CMS, SEO, animations, and A/B testing built-in. With Framer you can:

* Build fully responsive sites with no code
* Run experiments and publish updates instantly
* Manage content with built-in CMS and localization

I’m a big fan of products where it's obvious a lot of craft and heart went into it. Use code **PETERYANG2025** to get a free month of Framer Pro now.

[Start Building with Framer](https://framer.link/PeterYang)

---

## Why do AI evaluations matter?

[![](https://substackcdn.com/image/fetch/$s_!WQjV!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Feeca23ee-e240-4ff7-953d-b1cca331567e_1982x972.png)](https://substackcdn.com/image/fetch/$s_!WQjV!,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Feeca23ee-e240-4ff7-953d-b1cca331567e_1982x972.png)

AI evaluations help you measure the quality and effectiveness of your AI product.

Think of evals like unit tests for AI — except instead of checking if code compiles, you're checking if your AI gives good answers consistently.

There are four main types:

1. **Code-based eval**: Simple pass/fail checks (e.g., is "30-day return" in the response?).
2. **Human eval**: Human experts label AI's output against criteria you define.
3. **LLM judge eval**: Use another AI to evaluate your AI's responses at scale.
4. **User eval**: Test with real users and collect metrics and feedback.

Let me show you exactly how each type works with a real example.

---

## What we’ll build: AI evaluations for an ON running shoes support agent

[![](https://substackcdn.com/image/fetch/$s_!ft4r!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb3c286ad-0ebb-41e5-b692-aad1e12bd3c2_1600x1005.png)](https://substackcdn.com/image/fetch/$s_!ft4r!,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb3c286ad-0ebb-41e5-b692-aad1e12bd3c2_1600x1005.png)

Let’s pretend we’re the PM for ON’s AI customer support agent

I love running so let's build AI evaluations for a customer support agent for [ON running shoes](https://www.on.com/en-us/?srsltid=AfmBOopdD_af-K5-ZAUNHf0zmQ4NiZueayYGvdfz_uRXv_t6fR4Sv4Si). Like any good PM, let’s start by writing the shortest possible spec:

1. **Problem:** Customers want shoe recommendations and policy guidance, but human agents are expensive.
2. **Goal:** Answer 80% of inquiries accurately using ON's encouraging brand voice.
3. **Solution:** AI support agent trained on ON's product catalog and return policies.

Now let’s craft the AI prompt for our support agent.

---

## 1. Create your AI prompt

A good prompt should be grounded in ON’s product catalog and return policies:

[![](https://substackcdn.com/image/fetch/$s_!PFSk!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc26a9981-72a4-42d2-8fba-cef0251dcfb7_1920x953.png)](https://substackcdn.com/image/fetch/$s_!PFSk!,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc26a9981-72a4-42d2-8fba-cef0251dcfb7_1920x953.png)

I admit I may have asked ChatGPT to generate this 😅

Let’s be lazy and plug both artifacts into [Anthropic’s tool](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prompt-generator) to generate the prompt:

```
You are a helpful customer support agent for ON running shoes. Use the provided company policies and product information to answer customer questions accurately and helpfully.

Guidelines: 
- Always reference specific policies when discussing returns and more.
- Make personalized shoe recommendations based on the product info 
- Maintain ON's encouraging tone about running and fitness 
- Never make up policies or product details not in the provided context

Policy: {{COMPANY_POLICIES}} 
Product information: {{PRODUCT_LIST}} 

Customer Question: {{CUSTOMER_QUESTION}}
```

This looks solid. Now let’s work on our evals.

---

## 2. Run programmatic evals to catch obvious failures

Let’s start with code-based checks that can catch obvious problems like:

1. **Policy:** Check for incorrect text matches like “45-day return” instead of “30-day.”
2. **Brand:** Check for inappropriate language or mentions of competitors.
3. **Quality:** Catch responses that are way too short (under 50 characters) or too long (over 1000 characters).

Programmatic evals are fast and cheap but only work for rule-based criteria. For everything else, we need humans in the loop.

---

## 3. Use human evals to label your golden dataset

Human evals mean grading AI responses based on a set of **evaluation criteria**. This creates a **golden dataset** of human-labeled questions and answers that will be the foundation of all our other evals. Here's the workflow:

#### a) Draft your evaluation criteria

Let’s define three criteria for our AI agent based on our spec:

* **Accuracy:** Does the response match the product info and company policies?
* **Helpfulness:** Does the response actually solve the customer's problem?
* **Tone:** Does the response use ON's encouraging brand voice?

For each criteria, we need to define what a good, average, and bad response looks like:

[![](https://substackcdn.com/image/fetch/$s_!LZMS!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9eb308c5-946f-44d7-b60b-dc3fd0d897f6_1084x384.png)](https://substackcdn.com/image/fetch/$s_!LZMS!,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9eb308c5-946f-44d7-b60b-dc3fd0d897f6_1084x384.png)

#### b) Create test cases

Now that we have our criteria, let’s come up with test cases that cover common scenarios, edge cases, and adversarial questions from users:

* **Common:** "I'm training for my first marathon and need maximum cushioning. What shoe do you recommend?" 🏃
* **Edge case:** “I placed an order 45 minutes ago but need to change the delivery address. Is that possible?” 🥺
* **Adversarial:** "I bought these shoes 6 months ago and they're worn out. This is false advertising and I want a full refund or I'm disputing the charge." 😡

We eventually want at least 50 test cases to make statistically meaningful decisions about prompt changes, but a dozen should be enough to start with.

#### c) Label AI’s responses manually

Now we need to manually label AI's answers based on our criteria. Here's what a human label might look like for the edge case question above:

[![](https://substackcdn.com/image/fetch/$s_!g1fr!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2596518b-94bd-4e97-a102-da6025325cce_1163x552.png)](https://substackcdn.com/image/fetch/$s_!g1fr!,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2596518b-94bd-4e97-a102-da6025325cce_1163x552.png)

I’ve graded AI’s answer to this question as follows:

* **Accuracy: Bad** - Claims passed return window (60-min) when it’s only 45 min.
* **Helpfulness: Bad** - Gives wrong answer to customer's question.
* **Tone: Average** - Answer shows empathy but is too long.

Note that I've also added detailed notes that provide important context for improving prompts and training LLM judges in the next step.

#### d) Debug with other human labelers

Get each human labeler to label a dozen or so responses and then get everyone together to discuss questions like:

1. "If a response solves the customer's problem but reads like an essay, is that 'average' or 'bad' for tone given ON's brand voice?"
2. "Should we penalize helpfulness for responses that give the right policy information but don't provide next steps to actually resolve the user’s issue?"

This back-and-forth dialogue is essential to align on what good/average/bad looks like and to refine your evaluation criteria. When discussing, also consider whether your labelers have systematic biases (e.g., they’re all hardcore vs. casual runners). Once your labelers are calibrated, they should finish labeling the rest of the test cases.

#### e) Analyze failure patterns and improve your prompt

After labeling anywhere from a dozen to fifty responses, failure patterns should clearly emerge (or use another LLM to summarize your human label notes to find them). For our customer support agent, these failure patterns might include:

1. Overly verbose responses (appears in 18 responses)
2. Math/logic errors (appears in 12 responses)
3. Missing next steps for customers (appears in 15 responses)

Use these patterns to update your prompt. For example, you might add "Keep responses under 100 words" or "Always end with clear next steps for the customer."

> **This is the reality of human evals — it’s a lot of manual work in spreadsheets!**

Here are some tips to make this process less painful:

1. **Start small.** Don't try to label hundreds when you're still making major prompt changes. You'll waste time labeling data that becomes obsolete.
2. **Get multiple opinions.** Have multiple people score the same responses to calibrate each labeler's scores and refine your eval criteria.
3. **Write detailed notes.** You'll use these to improve your prompts and train LLM judges in the next step.

---

## 4. Scale with LLM judge evals

[![](https://substackcdn.com/image/fetch/$s_!EsoF!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1111c50e-024b-430f-9059-a816af3cd1be_680x477.png)](https://substackcdn.com/image/fetch/$s_!EsoF!,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1111c50e-024b-430f-9059-a816af3cd1be_680x477.png)

What I imagine an LLM judge looks like

Can you imagine manually labeling 50-100 responses every time you update your AI product’s prompt or data? It gives me a headache just thinking about it.

Luckily, LLM judges are here to help. An LLM judge is trained to grade responses just like your human experts do but can evaluate hundreds of responses in minutes instead of hours.

LLM judges seem magical but are easy to screw up. Here’s exactly how to set them up: