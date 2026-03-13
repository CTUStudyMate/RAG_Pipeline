import pipeline_config as conf
def get_batches(total_page):
    batches = []    
    if (total_page>conf.MAX_PAGES_PER_BATCH):
        # return the list of pages for batches
        batches = []
        i = 0
        while (i<total_page):
            current_tuple = [i]
            end_page = min(i+conf.MAX_PAGES_PER_BATCH-1, total_page-1)
            current_tuple.append(end_page)
            batches.append(current_tuple)
            i+=conf.MAX_PAGES_PER_BATCH

    else:
        batches = [[0, total_page-1]]
    
    return batches