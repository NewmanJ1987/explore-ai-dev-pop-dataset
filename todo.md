Preprocess datasets: Look for the following cases of the prs, get counts of each. Look for examples of each.  
* Problematic-Revised: Gold candidates where a reviewer requested changes and the PR was subsequently revised and approved only 427 cases. 
* Problematic-Reject: subset of 7270 prs that were closed without merge PRs. 
* * created and closed right away (filter as mistakes)
* * created had some review and then closed (pr had errors)
* * created closed for staleness, duplication, or merge conflicts (filter these out)
* Accepted: 3,444 pr had at least one approval before they were merged out of a subset of 24, 014 closed and merged PRs. 
* * Filter out ones that were just library changes, version updates, new releases. PRs that were just created that did not really affect Business logic. 
* Closed and merged PRs (No approvals)
* * Filter out for ones that had review messages before they were merged and closed. Approval is not mandatory for all repos. 
* * Filter out created, closed and merged quickly.  Could be just version updates. Filter out ones merged by bots. 



Lets start with these scenarios. 
