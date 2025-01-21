
def rebaseTimes(times, bib=None, col=None):
    if bib is None or col is None:
        return times
    return times[col] - times[times['team_bib']==bib][col].iloc[0]