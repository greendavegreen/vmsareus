from xkcdpass import xkcd_password as xp

def capitalize_first_letter(s):
    new_str = []
    s = s.split(" ")
    for i, c in enumerate(s):
        new_str.append(c.capitalize())
    return "".join(new_str)

def gen_dev_password():

    # create a wordlist from the default wordfile
    # use words between 5 and 8 letters long
    wordfile = xp.locate_wordfile()
    mywords = xp.generate_wordlist(wordfile=wordfile, min_length=3, max_length=8)

    res = xp.generate_xkcdpassword(mywords, numwords=3, acrostic='dev')
    # create a password with the acrostic "face"
    return capitalize_first_letter(res)
