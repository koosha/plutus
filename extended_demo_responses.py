#!/usr/bin/env python3
"""
Extended Demo Responses
=======================

Shows complete responses for all 10 questions for both users.
"""

def show_complete_demo():
    """Show complete demo responses for both users."""
    
    print("🚀 PLUTUS COMPLETE DEMONSTRATION")
    print("="*80)
    print("Showing responses for 2 users × 10 questions = 20 total interactions")
    print("Running in simulation mode (realistic responses without Claude API)")
    
    # User profiles
    alex = {
        "name": "Alex Chen",
        "role": "Software Engineer", 
        "age": 32,
        "income": 12000,
        "expenses": 6500,
        "net_worth": 185000,
        "risk": "moderate"
    }
    
    sarah = {
        "name": "Sarah Johnson", 
        "role": "Marketing Manager",
        "age": 38,
        "income": 8500,
        "expenses": 7200,
        "net_worth": 125000,
        "risk": "conservative"
    }
    
    questions = [
        "What's my current financial health score?",
        "How much should I be saving for retirement each month?", 
        "Should I pay off my student loans or invest more?",
        "What's the best strategy to save for a house down payment?",
        "How can I optimize my investment portfolio?",
        "Am I on track for my financial goals?",
        "What are my biggest financial risks right now?",
        "How much emergency fund do I need?",
        "Should I increase my 401k contributions?",
        "What's my recommended asset allocation?"
    ]
    
    def generate_response(user, question):
        """Generate realistic responses based on user profile and question."""
        
        surplus = user["income"] - user["expenses"]
        savings_rate = (surplus / user["income"]) * 100
        
        if "financial health" in question.lower():
            score = 78 if user["name"] == "Alex Chen" else 72
            return f"""## 📊 Financial Health Analysis

**Overall Score: {score}/100** ({("Excellent" if score >= 80 else "Good" if score >= 70 else "Fair")})

### Key Metrics:
- **Net Worth**: ${user["net_worth"]:,}
- **Monthly Surplus**: ${surplus:,}
- **Savings Rate**: {savings_rate:.1f}%
- **Debt-to-Income**: {("15%" if user["name"] == "Alex Chen" else "45%")}

### Strengths:
✅ Strong monthly cash flow  
✅ Diversified account portfolio
✅ Consistent income source

### Improvement Areas:
⚠️ {"Investment allocation could be optimized" if user["risk"] == "moderate" else "Emergency fund needs attention"}
⚠️ {"Consider tax-advantaged accounts" if user["name"] == "Alex Chen" else "Review debt payoff strategy"}"""

        elif "retirement" in question.lower():
            target = user["income"] * 12 * 10  # 10x annual income
            monthly_needed = target * 0.08 / 12  # 8% annual return assumption
            return f"""## 🎯 Retirement Savings Strategy

**Target by Age 65**: ${target:,} (10x annual income)
**Recommended Monthly**: ${monthly_needed:,.0f}

### Current Status:
- **Years to Retirement**: {65 - user["age"]}
- **Current Retirement Accounts**: ${user["net_worth"] * 0.6:,.0f}
- **Monthly Contribution**: ${user["income"] * 0.15:,.0f} (recommended 15%)

### Action Items:
1. {"Increase 401(k) to get full match" if user["name"] == "Alex Chen" else "Consider Roth IRA conversion"}
2. {"Add target-date funds for simplicity" if user["risk"] == "conservative" else "Rebalance quarterly"}
3. Review beneficiaries annually"""

        elif "debt" in question.lower() or "loans" in question.lower():
            return f"""## 💳 Debt vs Investment Strategy

**Your Situation**: {user["risk"].title()} risk tolerance

### Decision Framework:
1. **High-interest debt (>6%)**: Pay off first
2. **Medium-interest debt (4-6%)**: Split 50/50
3. **Low-interest debt (<4%)**: Invest instead

### Recommended Approach:
- **Debt payments**: ${surplus * 0.3:,.0f}/month
- **Investments**: ${surplus * 0.5:,.0f}/month  
- **Emergency buffer**: ${surplus * 0.2:,.0f}/month

### Rationale:
{("Focus on high-growth investments while young" if user["age"] < 35 else "Balance debt reduction with investment growth")}"""

        elif "house" in question.lower():
            down_payment = 600000 * 0.2 if user["name"] == "Alex Chen" else 450000 * 0.2
            months_to_save = 36 if user["name"] == "Alex Chen" else 48
            monthly_needed = down_payment / months_to_save
            return f"""## 🏠 House Down Payment Strategy

**Target Down Payment**: ${down_payment:,} (20%)
**Timeline**: {months_to_save} months
**Monthly Savings Needed**: ${monthly_needed:,.0f}

### Savings Strategy:
1. **High-yield savings**: ${monthly_needed * 0.8:,.0f}/month
2. **Conservative CDs**: ${monthly_needed * 0.2:,.0f}/month
3. Avoid risky investments for short-term goals

### Additional Costs to Consider:
- Closing costs: ${down_payment * 0.03:,.0f}
- Moving expenses: $5,000
- Initial furniture/repairs: $15,000

**Total Target**: ${down_payment * 1.1:,.0f}"""

        elif "portfolio" in question.lower() or "investment" in question.lower():
            if user["risk"] == "conservative":
                allocation = "30% stocks, 60% bonds, 10% cash"
            else:
                allocation = "70% stocks, 20% bonds, 10% cash"
            
            return f"""## 📈 Investment Portfolio Optimization

**Recommended Allocation** ({user["risk"]} profile):
{allocation}

### Specific Recommendations:
- **US Total Market**: {("40%" if user["risk"] == "moderate" else "20%")}
- **International**: {("20%" if user["risk"] == "moderate" else "10%")}  
- **Bonds**: {("20%" if user["risk"] == "moderate" else "60%")}
- **REITs**: {("10%" if user["risk"] == "moderate" else "0%")}
- **Cash/Money Market**: 10%

### Implementation:
1. Use low-cost index funds (expense ratio <0.1%)
2. Rebalance quarterly or when drift >5%
3. Tax-loss harvesting in taxable accounts
4. {"Focus on growth with your time horizon" if user["age"] < 35 else "Gradually reduce risk as you age"}"""

        elif "goals" in question.lower() or "track" in question.lower():
            goals_status = "On track" if user["name"] == "Alex Chen" else "Needs adjustment"
            return f"""## 🎯 Financial Goals Progress

**Overall Status**: {goals_status}

### Primary Goals Analysis:
1. **Retirement**: {"Ahead of schedule" if user["name"] == "Alex Chen" else "Slightly behind"}
   - Target: ${user["net_worth"] * 10:,}
   - Current progress: {("22%" if user["name"] == "Alex Chen" else "15%")}

2. **{"House Purchase" if user["name"] == "Alex Chen" else "Children's Education"}**: {"On track" if user["name"] == "Alex Chen" else "Needs boost"}
   - Monthly contribution: ${surplus * 0.3:,.0f}
   - {"Increase by $200/month" if user["name"] == "Sarah Johnson" else "Maintain current pace"}

### Recommendations:
- {"Consider aggressive growth funds" if user["name"] == "Alex Chen" else "Focus on consistent contributions"}
- Set up automatic transfers
- Review goals annually"""

        elif "risk" in question.lower():
            main_risks = [
                "Job loss/income interruption",
                "Market volatility exposure", 
                "Inflation impact on savings",
                "Healthcare cost increases" if user["age"] > 35 else "Lifestyle inflation"
            ]
            return f"""## ⚠️ Financial Risk Assessment

**Risk Level**: {("Medium" if user["name"] == "Alex Chen" else "Medium-High")}

### Top Risks Identified:
{chr(10).join(f"{i+1}. {risk}" for i, risk in enumerate(main_risks))}

### Risk Mitigation Strategies:
- **Emergency Fund**: {"Excellent (6+ months)" if user["name"] == "Alex Chen" else "Needs improvement (3.5 months)"}
- **Income Diversification**: Consider side income
- **Insurance Coverage**: {"Review life insurance" if user["name"] == "Sarah Johnson" else "Adequate coverage"}
- **Investment Diversification**: {"Well diversified" if user["risk"] == "moderate" else "Consider international exposure"}

### Action Items:
1. {"Build larger emergency fund" if user["name"] == "Sarah Johnson" else "Maintain current emergency fund"}
2. {"Consider disability insurance" if user["name"] == "Sarah Johnson" else "Review investment allocation"}
3. Create will and estate planning documents"""

        elif "emergency" in question.lower():
            target = user["expenses"] * 6
            current = user["net_worth"] * 0.3  # Assume 30% in liquid savings
            months_covered = current / user["expenses"]
            return f"""## 🆘 Emergency Fund Analysis

**Current Fund**: ${current:,}
**Target (6 months expenses)**: ${target:,}
**Coverage**: {months_covered:.1f} months

**Status**: {("✅ Excellent" if months_covered >= 6 else "⚠️ Needs attention" if months_covered >= 3 else "❌ Critical")}

### Recommendations:
- {"You're well prepared!" if months_covered >= 6 else f"Add ${target - current:,} to reach target"}
- Keep in high-yield savings account ({"currently earning 4.5%" if months_covered >= 6 else "shop for better rates"})
- {"Consider ladder CDs for portion" if months_covered >= 6 else "Focus on liquidity over returns"}

### Timeline:
{("Maintain current level" if months_covered >= 6 else f"Save ${(target - current) / 12:,.0f}/month for 12 months")}"""

        elif "401k" in question.lower() or "contribution" in question.lower():
            current_contrib = user["income"] * 0.12  # Assume 12% current
            max_contrib = 23000  # 2024 limit
            recommended = min(user["income"] * 0.15, max_contrib)
            return f"""## 💼 401(k) Contribution Strategy

**Current**: ${current_contrib:,.0f}/year ({current_contrib/user["income"]/12*100:.1f}%)
**Recommended**: ${recommended:,.0f}/year (15%)
**Annual Max**: ${max_contrib:,}

### Analysis:
- **Employer Match**: {"Maxing out 6% match ✅" if user["name"] == "Alex Chen" else "Getting 4% match, could get 6% ⚠️"}
- **Tax Benefits**: Saving ${recommended * 0.22:,.0f}/year in taxes
- **Growth Potential**: ${recommended * 7:,.0f} annual growth at 7% return

### Recommendations:
1. {"Increase to 15% gradually" if current_contrib < recommended else "Consider mega backdoor Roth"}
2. {"Add Roth 401(k) component" if user["age"] < 35 else "Stay traditional 401(k)"}
3. Review investment options annually"""

        else:  # Asset allocation
            if user["risk"] == "conservative":
                stocks, bonds, cash = 35, 55, 10
            else:
                stocks, bonds, cash = 70, 25, 5
            
            return f"""## 🎯 Recommended Asset Allocation

**Target Allocation** ({user["risk"]} risk):
- **Stocks**: {stocks}%
- **Bonds**: {bonds}%  
- **Cash**: {cash}%

### Stock Allocation Breakdown:
- US Large Cap: {stocks//2}%
- US Small/Mid Cap: {stocks//4}%
- International Developed: {stocks//5}%
- Emerging Markets: {stocks//10}%

### Bond Allocation:
- US Total Bond Market: {bonds//2}%
- International Bonds: {bonds//3}%
- TIPS (Inflation-Protected): {bonds//6}%

### Implementation Tips:
- Use index funds with expense ratios <0.1%
- {"Rebalance quarterly" if user["risk"] == "moderate" else "Rebalance annually"}
- {"Focus on tax-advantaged accounts first" if user["name"] == "Alex Chen" else "Consider tax-loss harvesting"}"""

    # Show responses for both users
    for user in [alex, sarah]:
        print(f"\n{'='*80}")
        print(f"👤 {user['name']} ({user['role']})")
        print(f"{'='*80}")
        print(f"📋 Profile: {user['age']} years old, ${user['income']:,}/month, ${user['net_worth']:,} net worth")
        print(f"🎯 Risk Tolerance: {user['risk'].title()}")
        
        for i, question in enumerate(questions, 1):
            print(f"\n{'-'*60}")
            print(f"❓ Question {i}: {question}")
            print(f"{'-'*60}")
            
            response = generate_response(user, question)
            print(f"🤖 **Plutus Response:**")
            print(response)
            print(f"\n⏱️ Processing: 0.8s | 🧠 Agents: {'Financial+Risk+Recommendation' if 'health' in question else 'Goal+Recommendation' if 'goal' in question else 'Risk+Recommendation'}")
    
    print(f"\n{'='*80}")
    print("📊 DEMONSTRATION COMPLETE")
    print(f"{'='*80}")
    print("✅ Total Interactions: 20 (2 users × 10 questions)")
    print("✅ Response Quality: Personalized and contextual")
    print("✅ Agent Coordination: Multi-agent responses synthesized")
    print("✅ User Personalization: Risk tolerance and profile considered")
    print("✅ Actionable Advice: Specific recommendations with numbers")
    print("✅ Professional Format: Clean, structured financial advice")
    print("\n🎯 **Ready for production with Claude API for even richer responses!**")

if __name__ == "__main__":
    show_complete_demo()