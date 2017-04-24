#   Program: bba.sh
#   Date: 10/16/16
#   Purpose: identify bad by admission code and parse through its history

#   ./bba.sh directory_of_repo regex

ADDITIONAL_HEADERS="Commit,Date,Parent1,Parent2"
SLOC_HEADERS="Path,Physical,Source,Comment,Single-line comment,Block comment,Mixed,Empty,To Do,Regex"

echo ${ADDITIONAL_HEADERS},${SLOC_HEADERS}

pushd $1 &>/dev/null
REGEX=${2:-"^.*(TODO|FIXME).*$"}
get_hash() {
    git show -s --format=%h    
}

get_parent_one() {
    git show HEAD^1 -s --format=%h
}

get_parent_two() {
    git show HEAD^2 -s --format=%h 2>/dev/null || echo ""
}

get_commit_author() {
    git log --format='%ae' $1
}

# $1 = GIT REVISION
get_date() {
    git show -s --format=%ai
}

get_author_email() {
    git log --format='%ae' $1
}

# $1 = GIT REVISION
sloc_for_rev() {
    git checkout $1 &> /dev/null
    echo $(get_hash),$(get_date),$(get_parent_one),$(get_parent_two),\
    $(sloc --format csv --format-option no-head --regex ${REGEX} .)
}

git fetch &> /dev/null
git reset --hard origin/master &> /dev/null

START_COMMIT=$(get_hash)

for commit in $(git log --first-parent --format="%h")
do
    sloc_for_rev $commit
done

git checkout $START_COMMIT
popd &> /dev/null

