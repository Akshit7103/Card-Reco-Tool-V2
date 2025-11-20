"""
Root Cause Analysis Service using OpenAI API
Analyzes reconciliation discrepancies and provides insights
"""

from openai import OpenAI
import json
import os
from typing import Dict, List, Optional


class RootCauseAnalyzer:
    """Service for performing root cause analysis on reconciliation discrepancies"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the root cause analyzer

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY environment variable)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.model = "gpt-3.5-turbo"

    def check_openai_availability(self) -> bool:
        """
        Check if OpenAI client is properly configured

        Returns:
            bool: True if OpenAI client is available, False otherwise
        """
        return self.client is not None and self.api_key is not None

    def generate_analysis(self, prompt: str) -> Optional[str]:
        """
        Generate analysis using OpenAI GPT model

        Args:
            prompt: The prompt to send to OpenAI

        Returns:
            str: Generated analysis or None if failed
        """
        try:
            if not self.check_openai_availability():
                return None

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial reconciliation expert specializing in card payment transaction analysis and fee reconciliation. Provide detailed, technical analysis of discrepancies."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1000
            )

            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content.strip()
            else:
                print("OpenAI API returned no choices")
                return None

        except Exception as e:
            print(f"Error generating analysis: {str(e)}")
            return None

    def analyze_reconciliation_discrepancies(self, report: Dict) -> Optional[str]:
        """
        Analyze reconciliation discrepancies and generate root cause analysis

        Args:
            report: Report context with reconciliation data

        Returns:
            str: Root cause analysis or None if not needed/failed
        """
        # Check if analysis is needed (Amount Reconciled < 95%)
        amount_reconciled = report.get("summary", {}).get("amount_reconciled_percentage", 100)

        if amount_reconciled >= 95:
            return None  # No analysis needed

        # Check if OpenAI is available
        if not self.check_openai_availability():
            return "❌ Root Cause Analysis unavailable: OpenAI API key is not configured. Please set the OPENAI_API_KEY environment variable."

        # Gather discrepancy data
        discrepancies = self._extract_discrepancies(report)

        if not discrepancies:
            return "No significant discrepancies found to analyze."

        # Build analysis prompt
        prompt = self._build_analysis_prompt(report, discrepancies)

        # Generate analysis
        analysis = self.generate_analysis(prompt)

        if analysis:
            # Format the analysis for better HTML rendering
            analysis = self._format_analysis_html(analysis)

        return analysis

    def _format_analysis_html(self, analysis: str) -> str:
        """
        Format the analysis text with proper HTML for better rendering

        Args:
            analysis: Raw analysis text from OpenAI

        Returns:
            str: HTML-formatted analysis
        """
        import re

        # First, detect and format PART headers (e.g., "**PART 1: FEE-BY-FEE ANALYSIS**")
        # Match with optional ** around the text
        analysis = re.sub(
            r'(?:^|\n)\*{0,2}(PART\s+\d+:?\s*[A-Z\s\-]+?)\*{0,2}(?:\n|$)',
            r'\n<h3>\1</h3>\n',
            analysis,
            flags=re.MULTILINE
        )

        # Format numbered fee sections (e.g., "**1. Integrity Fee variance (+56.9%)**")
        # Match: "**Number. Fee Name variance (±X.X%)**"
        analysis = re.sub(
            r'(?:^|\n)\*{0,2}(\d+\.\s+[A-Za-z\s\-]+?(?:Fee|Fees))\s+(?:variance\s+)?\(([\+\-][\d\.]+%)\)\*{0,2}',
            r'\n<h4>\1 (\2)</h4>\n',
            analysis,
            flags=re.MULTILINE
        )

        # Format fee-specific subsections without numbers (e.g., "Integrity Fee variance (+56.9%)")
        analysis = re.sub(
            r'(?:^|\n)\*{0,2}([A-Za-z\s\-]+?(?:Fee|Fees))\s+(?:variance\s+)?\(([\+\-][\d\.]+%)\)\*{0,2}',
            r'\n<h4>\1 (\2)</h4>\n',
            analysis,
            flags=re.MULTILINE
        )

        # Format "Missing Fee Lines" or similar section headers
        analysis = re.sub(
            r'(?:^|\n)\*{0,2}(Missing\s+[A-Za-z\s]+|Overall\s+[A-Za-z\s]+)\*{0,2}(?:\n|$)',
            r'\n<h4>\1</h4>\n',
            analysis,
            flags=re.MULTILINE
        )

        # Split into lines for processing
        lines = analysis.split('\n')
        formatted_lines = []
        in_list = False
        in_causes_section = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty lines when not in a list
            if not stripped:
                if in_list:
                    formatted_lines.append('</ul>')
                    in_list = False
                    in_causes_section = False
                continue

            # Check for "Possible causes:" text
            if stripped.lower().startswith('possible cause'):
                if in_list:
                    formatted_lines.append('</ul>')
                    in_list = False
                formatted_lines.append(f'<p><strong>{stripped}</strong></p>')
                in_causes_section = True
                continue

            # Check if line starts with bullet point (•, -, or *)
            if re.match(r'^[•\-\*]\s+', stripped):
                if not in_list:
                    formatted_lines.append('<ul class="analysis-list">')
                    in_list = True
                # Remove bullet and wrap in list item
                content = re.sub(r'^[•\-\*]\s+', '', stripped)
                formatted_lines.append(f'<li>{content}</li>')

            # Check if it's an already formatted header (h3 or h4)
            elif '<h3>' in stripped or '<h4>' in stripped:
                if in_list:
                    formatted_lines.append('</ul>')
                    in_list = False
                    in_causes_section = False
                formatted_lines.append(stripped)

            # Regular text lines
            else:
                if in_list and not in_causes_section:
                    formatted_lines.append('</ul>')
                    in_list = False
                    in_causes_section = False

                # Don't wrap very short lines (likely incomplete)
                if len(stripped) > 5:
                    formatted_lines.append(f'<p>{stripped}</p>')

        # Close list if still open at the end
        if in_list:
            formatted_lines.append('</ul>')

        # Join and clean up multiple consecutive paragraph tags
        result = '\n'.join(formatted_lines)
        result = re.sub(r'</p>\s*<p>', '</p>\n<p>', result)

        # Convert any remaining Markdown bold syntax (**text**) to HTML bold
        # This handles bold text that wasn't part of headers or section titles
        result = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', result)

        return result

    def _extract_discrepancies(self, report: Dict) -> List[Dict]:
        """
        Extract fee types with significant discrepancies

        Args:
            report: Report context

        Returns:
            list: List of discrepancy details
        """
        discrepancies = []

        sheets = report.get("sheets", [])

        for sheet in sheets:
            rows = sheet.get("rows", [])

            for row in rows:
                fee_type = row.get("fee_type", "Unknown")
                percentage_diff = row.get("percentage_diff")
                diff_status = row.get("diff_status", "")
                calculated_amount_display = row.get("calculated_amount_display", "N/A")
                visa_amount_display = row.get("visa_amount_display", "N/A")
                final_amount_display = row.get("final_amount_display", "N/A")
                calculation_method = row.get("calculation_method", "N/A")

                # Only include items with actual discrepancies
                if diff_status in ["higher", "lower", "missing"]:
                    discrepancies.append({
                        "fee_type": fee_type,
                        "percentage_diff": percentage_diff,
                        "diff_status": diff_status,
                        "calculated_value": final_amount_display,
                        "visa_value": visa_amount_display,
                        "calculation_method": calculation_method,
                        "percentage_diff_display": row.get("percentage_diff_display", "N/A")
                    })

        return discrepancies

    def _build_analysis_prompt(self, report: Dict, discrepancies: List[Dict]) -> str:
        """
        Build the prompt for OpenAI to analyze discrepancies

        Args:
            report: Report context
            discrepancies: List of discrepancy details

        Returns:
            str: Formatted prompt
        """
        summary = report.get("summary", {})

        prompt = f"""You are a financial reconciliation expert. Analyze the following reconciliation discrepancies and provide a root cause analysis.

RECONCILIATION SUMMARY:
- Amount Reconciled: {summary.get('amount_reconciled_display', 'N/A')}
- Fee Reconciled: {summary.get('fee_reconciled_display', 'N/A')}
- Items Reconciled: {summary.get('matched_items', 0)}/{summary.get('total_visa_items', 0)}
- Calculated Total: {summary.get('total_final_amount_display', 'N/A')}
- VISA Invoice Total: {summary.get('total_visa_amount_display', 'N/A')}

IDENTIFIED DISCREPANCIES:
"""

        for i, disc in enumerate(discrepancies, 1):
            prompt += f"""
{i}. {disc['fee_type']}
   - Calculated Value: {disc['calculated_value']}
   - VISA Invoice Value: {disc['visa_value']}
   - Difference: {disc['percentage_diff_display']}
   - Status: {disc['diff_status']}
   - Calculation Method: {disc['calculation_method']}
"""

        prompt += """
TASK:
Provide a detailed, fee-specific root cause analysis of why these discrepancies exist.

FORMATTING REQUIREMENTS:
- Use clear structure with numbered sections and subsections
- Use bullet points (•) for listing causes
- Keep each point concise and specific
- Use proper paragraph breaks between sections
- Reference exact fee names and percentages from the data

ANALYSIS STRUCTURE:

PART 1: FEE-BY-FEE ANALYSIS
For EACH fee type listed above with a discrepancy, provide:
- Fee name with variance percentage in parentheses (e.g., "Integrity Fee variance (+56.9%)")
- Brief description of the discrepancy (calculated vs VISA)
- "Possible causes:" followed by bullet points with specific root causes

Example format for each fee:
Fee Name variance (+X.X%)
Brief description.
Possible causes:
• Specific cause related to this fee (e.g., tier application, rate mismatch)
• Data quality issue specific to this fee
• FX conversion or timing issue if applicable

PART 2: MISSING FEES ANALYSIS
If there are fees showing "Missing" status:
- List which fees are missing
- Explain what "Missing Calculations" means
- Connect to reconciliation metrics (Item Reconciled, Match %)

PART 3: OVERALL PATTERNS
Identify cross-cutting issues:
• Systematic problems affecting multiple fees
• Common root causes across fee types
• Data quality patterns

IMPORTANT RULES:
- Provide ONLY analysis, NO recommendations or action items
- Be VERY specific - reference actual amounts, rates, and percentages
- For each fee, identify the MOST PROBABLE specific root cause
- Focus on technical/operational causes (formulas, data, rates, mapping)
- Keep total length 400-600 words
- Use technical terminology appropriately (FX conversion, tier application, fee mapping, etc.)

ROOT CAUSE ANALYSIS:"""

        return prompt


def generate_root_cause_analysis(report: Dict, api_key: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to generate root cause analysis

    Args:
        report: Report context with reconciliation data
        api_key: Optional OpenAI API key (defaults to OPENAI_API_KEY environment variable)

    Returns:
        str: Root cause analysis or None
    """
    analyzer = RootCauseAnalyzer(api_key=api_key)
    return analyzer.analyze_reconciliation_discrepancies(report)
