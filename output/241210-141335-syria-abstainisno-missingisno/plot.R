library(pscl)
library(dwnominate)
library(wnominate)

# Folder containing the results relative to current working directory
input_folder <- "/Users/benjaminroberts/projects/nominate/unhrc-nominate/output/241210-141335-syria-abstainisno-missingisno/"

# Used to iterate through each year of UNHRC data
unhrc_year_first <- 2006
unhrc_year_last  <- 2024

n_min_votes = 2 # EDIT THIS

load_rollcall <- function(prefix)
{
    rollcall_df <- read.csv(paste0(input_folder, prefix, '-votes.csv'), header = TRUE, row.names=1)
    country_df <- read.csv(paste0(input_folder, prefix, '-legis-data.csv'), header = TRUE)
    vote_df <- read.csv(paste0(input_folder, prefix, '-vote-data.csv'), header = TRUE)

    vote_names <- colnames(rollcall_df)
    coutry_names <- country_df[,1]
    data = as.matrix(rollcall_df)

    rc <- pscl::rollcall(
        data,
        yea=1,
        nay=0,
        missing=c(2,3), 
        notInLegis=4,
        vote.names=vote_names,
        vote.data=vote_df,
        legis.names=coutry_names,
        legis.data=country_df)

    return(rc)
}

polarity <- c("CHN") # Change this to country code of polar extreme
unhrc_all_years = load_rollcall('all')


all_wnom <- wnominate(unhrc_all_years, dims=1, minvotes=n_min_votes, polarity=polarity)
png(filename="/Users/benjaminroberts/projects/nominate/unhrc-nominate/output/241210-141335-syria-abstainisno-missingisno/wnominate.png")
plot.coords(all_wnom)
dev.off()

chn_usa_wnom <- wnominate(unhrc_all_years, dims=2, minvotes=n_min_votes, polarity=c("CHN", "USA"))
png(filename="/Users/benjaminroberts/projects/nominate/unhrc-nominate/output/241210-141335-syria-abstainisno-missingisno/wnominate-CHN-USA.png")
plot.coords(chn_usa_wnom, d1.title="CHN Dimension Nominate", d2.title="USA Dimension Nominate" )
dev.off()